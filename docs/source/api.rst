Hyper-h2 API
============

This document details the API of Hyper-h2.

Semantic Versioning
-------------------

Hyper-h2 follows semantic versioning for its public API. Please note that the
guarantees of semantic versioning apply only to the API that is *documented
here*. Simply because a method or data field is not prefaced by an underscore
does not make it part of Hyper-h2's public API. Anything not documented here is
subject to change at any time.

Connection
----------

.. autoclass:: h2.connection.H2Connection
   :members:


.. _h2-events-api:

Events
------

.. autoclass:: h2.events.RequestReceived
   :members:

.. autoclass:: h2.events.ResponseReceived
   :members:

.. autoclass:: h2.events.TrailersReceived
   :members:

.. autoclass:: h2.events.DataReceived
   :members:

.. autoclass:: h2.events.WindowUpdated
   :members:

.. autoclass:: h2.events.RemoteSettingsChanged
   :members:

.. autoclass:: h2.events.PingAcknowledged
   :members:

.. autoclass:: h2.events.StreamEnded
   :members:

.. autoclass:: h2.events.StreamReset
   :members:

.. autoclass:: h2.events.PushedStreamReceived
   :members:

.. autoclass:: h2.events.SettingsAcknowledged
   :members:

.. autoclass:: h2.events.PriorityUpdated
   :members:

.. autoclass:: h2.events.ConnectionTerminated
   :members:


Exceptions
----------

.. autoclass:: h2.exceptions.H2Error
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.NoSuchStreamError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.StreamClosedError
   :show-inheritance:
   :members:


Protocol Errors
~~~~~~~~~~~~~~~

.. autoclass:: h2.exceptions.ProtocolError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.FrameTooLargeError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.FrameDataMissingError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.TooManyStreamsError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.FlowControlError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.StreamIDTooLowError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.InvalidSettingsValueError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.NoAvailableStreamIDError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.InvalidBodyLengthError
   :show-inheritance:
   :members:

.. autoclass:: h2.exceptions.UnsupportedFrameError
   :show-inheritance:
   :members:


HTTP/2 Error Codes
------------------

.. automodule:: h2.errors
   :members:


Settings
--------

.. autoclass:: h2.settings.Settings
   :inherited-members:

.. autoclass:: h2.settings.ChangedSetting
   :members:

Known Settings
~~~~~~~~~~~~~~

.. versionadded:: 2.0.0

.. autodata:: h2.settings.HEADER_TABLE_SIZE

.. autodata:: h2.settings.ENABLE_PUSH

.. autodata:: h2.settings.MAX_CONCURRENT_STREAMS

.. autodata:: h2.settings.INITIAL_WINDOW_SIZE

.. autodata:: h2.settings.MAX_FRAME_SIZE
