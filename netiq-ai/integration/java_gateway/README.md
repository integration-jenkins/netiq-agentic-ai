# Java gateway (sample)

The Java layer authenticates the NETIQ user and forwards the chat request to the Python service
over a trusted internal channel, passing the user identity and circle scope.

Example call:

```
POST /v1/chat
X-Correlation-Id: <uuid>
X-User-Id: <netiq user>
{ "session_id": "abc", "message": "Show RAN KPI for Delhi" }
```
