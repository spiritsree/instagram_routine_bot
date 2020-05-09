# Instagram Bot

A simple bot program to do stuff on Instagram via docker client.

## Quick Start

```
docker run --name=instagram-bot --rm -d \
           -v ~/Documents/IG_DATA:/data \
           -e ENABLE_DEBUG=true \
           -e IG_USERNAME='' \
           -e IG_PASSWORD=''
           instragram_bot:latest
```

## Documentation

* [Common Issues](./doc/issues.md)

## Reference

* [Instagram Private API Repo](https://github.com/ping/instagram_private_api)
* [Instagram Private API Doc](https://instagram-private-api.readthedocs.io/en/latest/index.html)

## License

GPL-3.0
