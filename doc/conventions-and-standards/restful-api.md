# **RESTFUL API**

- Must follow the [JSON API specification](https://jsonapi.org/) for request query strings. The response envelope
  is defined under [Conventions](coding.md#conventions)
- Must not create a GET endpoint that modifies data or that uses a request body. A query string or route parameter
  only gets or targets data. _Ex: `POST /medias/{media_id}/thumbnails` targets `media_id`. Width and height come
  from the body_
- Should use snake_case for response fields and request parameters. _Ex: `translated_text`, `source_language`,
  `thumbnail_signed_url`_
- Should avoid multi-purpose endpoints. One route performs one action
