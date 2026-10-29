Bugpipe
==========

Unofficial Python client for the Google Issue Tracking system (Buganizer).


Quick Start
-----------

.. code-block:: bash

   bugpipe search "status:open" -l 25 -t chromium -t webrtc -t fuchsia


.. code-block:: python

   from bugpipe import Bugpipe

   client = Bugpipe(trackers=["chromium", "webrtc", "fuchsia"])
   results = client.search(query="status:open priority:p1", per_page=25)
   for issue in results.issues:
     print(f"#{issue.id} [{issue.status.name}] {issue.title}")


.. toctree::
   :hidden:

   installation
   usage
   api
   audit
