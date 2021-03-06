# -*- coding: utf-8 -*-
"""
test_complex_logic
~~~~~~~~~~~~~~~~

More complex tests that try to do more.

Certain tests don't really eliminate incorrect behaviour unless they do quite
a bit. These tests should live here, to keep the pain in once place rather than
hide it in the other parts of the test suite.
"""
import pytest

import h2
import h2.connection


class TestComplexClient(object):
    """
    Complex tests for client-side stacks.
    """
    example_request_headers = [
        (':authority', 'example.com'),
        (':path', '/'),
        (':scheme', 'https'),
        (':method', 'GET'),
    ]
    example_response_headers = [
        (':status', '200'),
        ('server', 'fake-serv/0.1.0')
    ]

    def test_correctly_count_server_streams(self, frame_factory):
        """
        We correctly count the number of server streams, both inbound and
        outbound.
        """
        # This test makes no sense unless you do both inbound and outbound,
        # because it's important to confirm that we count them correctly.
        c = h2.connection.H2Connection(client_side=True)
        c.initiate_connection()
        expected_inbound_streams = expected_outbound_streams = 0

        assert c.open_inbound_streams == expected_inbound_streams
        assert c.open_outbound_streams == expected_outbound_streams

        for stream_id in range(1, 15, 2):
            # Open an outbound stream
            c.send_headers(stream_id, self.example_request_headers)
            expected_outbound_streams += 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            # Receive a pushed stream (to create an inbound one). This doesn't
            # open until we also receive headers.
            f = frame_factory.build_push_promise_frame(
                stream_id=stream_id,
                promised_stream_id=stream_id+1,
                headers=self.example_request_headers,
            )
            c.receive_data(f.serialize())
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            f = frame_factory.build_headers_frame(
                stream_id=stream_id+1,
                headers=self.example_response_headers,
            )
            c.receive_data(f.serialize())
            expected_inbound_streams += 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

        for stream_id in range(13, 0, -2):
            # Close an outbound stream.
            c.end_stream(stream_id)

            # Stream doesn't close until both sides close it.
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            f = frame_factory.build_headers_frame(
                stream_id=stream_id,
                headers=self.example_response_headers,
                flags=['END_STREAM'],
            )
            c.receive_data(f.serialize())
            expected_outbound_streams -= 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            # Pushed streams can only be closed remotely.
            f = frame_factory.build_headers_frame(
                stream_id=stream_id+1,
                headers=self.example_response_headers,
                flags=['END_STREAM'],
            )
            c.receive_data(f.serialize())
            expected_inbound_streams -= 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

        assert c.open_inbound_streams == 0
        assert c.open_outbound_streams == 0


class TestComplexServer(object):
    """
    Complex tests for server-side stacks.
    """
    example_request_headers = [
        (':authority', 'example.com'),
        (':path', '/'),
        (':scheme', 'https'),
        (':method', 'GET'),
    ]
    example_response_headers = [
        (':status', '200'),
        ('server', 'fake-serv/0.1.0')
    ]

    def test_correctly_count_server_streams(self, frame_factory):
        """
        We correctly count the number of server streams, both inbound and
        outbound.
        """
        # This test makes no sense unless you do both inbound and outbound,
        # because it's important to confirm that we count them correctly.
        c = h2.connection.H2Connection(client_side=False)
        c.receive_data(frame_factory.preamble())
        expected_inbound_streams = expected_outbound_streams = 0

        assert c.open_inbound_streams == expected_inbound_streams
        assert c.open_outbound_streams == expected_outbound_streams

        for stream_id in range(1, 15, 2):
            # Receive an inbound stream.
            f = frame_factory.build_headers_frame(
                headers=self.example_request_headers,
                stream_id=stream_id,
            )
            c.receive_data(f.serialize())
            expected_inbound_streams += 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            # Push a stream (to create a outbound one). This doesn't open
            # until we send our response headers.
            c.push_stream(stream_id, stream_id+1, self.example_request_headers)
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            c.send_headers(stream_id+1, self.example_response_headers)
            expected_outbound_streams += 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

        for stream_id in range(13, 0, -2):
            # Close an inbound stream.
            f = frame_factory.build_data_frame(
                data=b'',
                flags=['END_STREAM'],
                stream_id=stream_id,
            )
            c.receive_data(f.serialize())

            # Stream doesn't close until both sides close it.
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            c.send_data(stream_id, b'', end_stream=True)
            expected_inbound_streams -= 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

            # Pushed streams, however, we can close ourselves.
            c.send_data(
                stream_id=stream_id+1,
                data=b'',
                end_stream=True,
            )
            expected_outbound_streams -= 1
            assert c.open_inbound_streams == expected_inbound_streams
            assert c.open_outbound_streams == expected_outbound_streams

        assert c.open_inbound_streams == 0
        assert c.open_outbound_streams == 0


class TestContinuationFrames(object):
    """
    Tests for the relatively complex CONTINUATION frame logic.
    """
    example_request_headers = [
        (':authority', 'example.com'),
        (':path', '/'),
        (':scheme', 'https'),
        (':method', 'GET'),
    ]

    def _build_continuation_sequence(self, headers, block_size, frame_factory):
        f = frame_factory.build_headers_frame(headers)
        header_data = f.data
        chunks = [
            header_data[x:x+block_size]
            for x in range(0, len(header_data), block_size)
        ]
        f.data = chunks.pop(0)
        frames = [
            frame_factory.build_continuation_frame(c) for c in chunks
        ]
        f.flags = set(['END_STREAM'])
        frames[-1].flags.add('END_HEADERS')
        frames.insert(0, f)
        return frames

    def test_continuation_frame_basic(self, frame_factory):
        """
        Test that we correctly decode a header block split across continuation
        frames.
        """
        c = h2.connection.H2Connection(client_side=False)
        c.initiate_connection()
        c.receive_data(frame_factory.preamble())

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        data = b''.join(f.serialize() for f in frames)
        events = c.receive_data(data)

        assert len(events) == 2
        first_event, second_event = events

        assert isinstance(first_event, h2.events.RequestReceived)
        assert first_event.headers == self.example_request_headers
        assert first_event.stream_id == 1

        assert isinstance(second_event, h2.events.StreamEnded)
        assert second_event.stream_id == 1

    @pytest.mark.parametrize('stream_id', [3, 1])
    def test_continuation_cannot_interleave_headers(self,
                                                    frame_factory,
                                                    stream_id):
        """
        We cannot interleave a new headers block with a CONTINUATION sequence.
        """
        c = h2.connection.H2Connection(client_side=False)
        c.initiate_connection()
        c.receive_data(frame_factory.preamble())
        c.clear_outbound_data_buffer()

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_headers_frame(
            headers=self.example_request_headers,
            stream_id=stream_id,
            flags=['END_STREAM'],
        )
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()

    def test_continuation_cannot_interleave_data(self, frame_factory):
        """
        We cannot interleave a data frame with a CONTINUATION sequence.
        """
        c = h2.connection.H2Connection(client_side=False)
        c.initiate_connection()
        c.receive_data(frame_factory.preamble())
        c.clear_outbound_data_buffer()

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_data_frame(
            data=b'hello',
            stream_id=1,
        )
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()

    def test_continuation_cannot_interleave_unknown_frame(self, frame_factory):
        """
        We cannot interleave an unknown frame with a CONTINUATION sequence.
        """
        c = h2.connection.H2Connection(client_side=False)
        c.initiate_connection()
        c.receive_data(frame_factory.preamble())
        c.clear_outbound_data_buffer()

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_data_frame(
            data=b'hello',
            stream_id=1,
        )
        bogus_frame.type = 88
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()


class TestContinuationFramesPushPromise(object):
    """
    Tests for the relatively complex CONTINUATION frame logic working with
    PUSH_PROMISE frames.
    """
    example_request_headers = [
        (':authority', 'example.com'),
        (':path', '/'),
        (':scheme', 'https'),
        (':method', 'GET'),
    ]
    example_response_headers = [
        (':status', '200'),
        ('server', 'fake-serv/0.1.0')
    ]

    def _build_continuation_sequence(self, headers, block_size, frame_factory):
        f = frame_factory.build_push_promise_frame(
            stream_id=1, promised_stream_id=2, headers=headers
        )
        header_data = f.data
        chunks = [
            header_data[x:x+block_size]
            for x in range(0, len(header_data), block_size)
        ]
        f.data = chunks.pop(0)
        frames = [
            frame_factory.build_continuation_frame(c) for c in chunks
        ]
        f.flags = set(['END_STREAM'])
        frames[-1].flags.add('END_HEADERS')
        frames.insert(0, f)
        return frames

    def test_continuation_frame_basic_push_promise(self, frame_factory):
        """
        Test that we correctly decode a header block split across continuation
        frames when that header block is initiated with a PUSH_PROMISE.
        """
        c = h2.connection.H2Connection(client_side=True)
        c.initiate_connection()
        c.send_headers(stream_id=1, headers=self.example_request_headers)

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        data = b''.join(f.serialize() for f in frames)
        events = c.receive_data(data)

        assert len(events) == 1
        event = events[0]

        assert isinstance(event, h2.events.PushedStreamReceived)
        assert event.headers == self.example_request_headers
        assert event.parent_stream_id == 1
        assert event.pushed_stream_id == 2

    @pytest.mark.parametrize('stream_id', [3, 1, 2])
    def test_continuation_cannot_interleave_headers_pp(self,
                                                       frame_factory,
                                                       stream_id):
        """
        We cannot interleave a new headers block with a CONTINUATION sequence
        when the headers block is based on a PUSH_PROMISE frame.
        """
        c = h2.connection.H2Connection(client_side=True)
        c.initiate_connection()
        c.send_headers(stream_id=1, headers=self.example_request_headers)

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_headers_frame(
            headers=self.example_response_headers,
            stream_id=stream_id,
            flags=['END_STREAM'],
        )
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()

    def test_continuation_cannot_interleave_data(self, frame_factory):
        """
        We cannot interleave a data frame with a CONTINUATION sequence when
        that sequence began with a PUSH_PROMISE frame.
        """
        c = h2.connection.H2Connection(client_side=True)
        c.initiate_connection()
        c.send_headers(stream_id=1, headers=self.example_request_headers)

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_data_frame(
            data=b'hello',
            stream_id=1,
        )
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()

    def test_continuation_cannot_interleave_unknown_frame(self, frame_factory):
        """
        We cannot interleave an unknown frame with a CONTINUATION sequence when
        that sequence began with a PUSH_PROMISE frame.
        """
        c = h2.connection.H2Connection(client_side=True)
        c.initiate_connection()
        c.send_headers(stream_id=1, headers=self.example_request_headers)

        frames = self._build_continuation_sequence(
            headers=self.example_request_headers,
            block_size=5,
            frame_factory=frame_factory,
        )
        assert len(frames) > 2  # This is mostly defensive.

        bogus_frame = frame_factory.build_data_frame(
            data=b'hello',
            stream_id=1,
        )
        bogus_frame.type = 88
        frames.insert(len(frames) - 2, bogus_frame)
        data = b''.join(f.serialize() for f in frames)

        with pytest.raises(h2.exceptions.ProtocolError) as e:
            c.receive_data(data)

        assert "invalid frame" in str(e.value).lower()
