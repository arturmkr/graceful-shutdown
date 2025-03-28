```
curl -X 'POST' \
  'http://172.17.1.4:8000/sync-task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "iterations": 3
}'
```

```
curl -X 'POST' \
  'http://172.17.1.4:8000/async-task' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "iterations": 60
}'
```

```
curl -X 'GET' \
  'http://172.17.1.4:8000/task/f8fa3155-1bd7-45bf-91c3-bc5180e0e08a' \
  -H 'accept: application/json'
```