```
curl -X 'POST' \
  'http://0.0.0.0:8000/sync-task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "iterations": 3
}'
```

```
curl -X 'POST' \
  'http://0.0.0.0:8000/async-task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "iterations": 5
}'
```

```
curl -X 'GET' \
  'http://0.0.0.0:8000/task/123' \
  -H 'accept: application/json'
```