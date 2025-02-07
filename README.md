# hook2mail

A simple webservice that forwards any e-mail message posted on `/webhook` endpoint to a list of recipients.

example :

```shell
MESSAGE="$(echo 'hello word !' | base64 | jq -R '{ "message": . }')"
curl -X POST -H "Content-Type: application/json" localhost:8000/webhook -d "${MESSAGE}"
```
