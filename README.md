<p align="center">
<img alt="logo" src="https://www.gstatic.com/buganizer/img/v0/logo.svg" width="150" height="150">
<br>
<br>
Unofficial Python client for the Google Issue Tracking system (Buganizer)
</p>

## Quick Start

```bash
bugpipe search "status:open" -l 25 -t chromium -t webrtc -t fuchsia
```

```python
from bugpipe import Bugpipe

with Bugpipe(trackers=["chromium", "webrtc", "fuchsia"]) as client:
    result = client.search(query="status:open priority:p1", page_size=25)
    for issue in result.issues:
        print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

## Documentation

Refer to [the docs](https://bugpipe.readthedocs.io) for installation, usage and api reference.
