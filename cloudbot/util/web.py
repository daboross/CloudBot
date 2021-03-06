""" web.py - web services and more """

import json

import requests

# Constants

DEFAULT_SHORTENER = 'qx.lc'
DEFAULT_PASTEBIN = 'qx.lc'

HASTEBIN_SERVER = 'http://hastebin.com'

# Python eval

def pyeval(code, pastebin=True):
    p = {'input': code}
    r = requests.post('http://pyeval.appspot.com/exec', data=p)

    p = {'id': r.text}
    r = requests.get('http://pyeval.appspot.com/exec', params=p)
    j = r.json()

    output = j['output'].rstrip('\n')
    if '\n' in output and pastebin:
        return paste(output)
    else:
        return output


# Shortening / pasting

# Public API


def shorten(url, custom=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.shorten(url, custom)


def try_shorten(url, custom=None, service=DEFAULT_SHORTENER):
    impl = shorteners[service]
    return impl.try_shorten(url, custom)


def expand(url, service=None):
    if service:
        impl = shorteners[service]
    else:
        impl = None
        for name in shorteners:
            if name in url:
                impl = shorteners[name]
                break

        if impl is None:
            impl = Shortener()

    return impl.expand(url)


def paste(data, ext='txt', service=DEFAULT_PASTEBIN):
    impl = pastebins[service]
    return impl.paste(data, ext)


class ServiceError(Exception):
    def __init__(self, message, request):
        self.message = message
        self.request = request

    def __str__(self):
        return '[HTTP {}] {}'.format(self.request.status_code, self.message)


class Shortener:
    def __init__(self):
        pass

    def shorten(self, url, custom=None):
        return url

    def try_shorten(self, url, custom=None):
        try:
            return self.shorten(url, custom)
        except ServiceError:
            return url

    def expand(self, url):
        r = requests.get(url, allow_redirects=False)

        if 'location' in r.headers:
            return r.headers['location']
        else:
            raise ServiceError('That URL does not exist', r)


class Pastebin:
    def __init__(self):
        pass

    def paste(self, data, ext):
        raise NotImplementedError

# Internal Implementations

shorteners = {}
pastebins = {}


def _shortener(name):
    def _decorate(impl):
        shorteners[name] = impl()

    return _decorate


def _pastebin(name):
    def _decorate(impl):
        pastebins[name] = impl()

    return _decorate


@_shortener('is.gd')
class Isgd(Shortener):
    def shorten(self, url, custom=None):
        p = {'url': url, 'shorturl': custom, 'format': 'json'}
        r = requests.get('http://is.gd/create.php', params=p)
        j = r.json()

        if 'shorturl' in j:
            return j['shorturl']
        else:
            raise ServiceError(j['errormessage'], r)

    def expand(self, url):
        p = {'shorturl': url, 'format': 'json'}
        r = requests.get('http://is.gd/forward.php', params=p)
        j = r.json()

        if 'url' in j:
            return j['url']
        else:
            raise ServiceError(j['errormessage'], r)


@_shortener('goo.gl')
class Googl(Shortener):
    def shorten(self, url, custom=None):
        h = {'content-type': 'application/json'}
        p = {'longUrl': url}
        r = requests.post('https://www.googleapis.com/urlshortener/v1/url', data=json.dumps(p), headers=h)
        j = r.json()

        if 'error' not in j:
            return j['id']
        else:
            raise ServiceError(j['error']['message'], r)

    def expand(self, url):
        p = {'shortUrl': url}
        r = requests.get('https://www.googleapis.com/urlshortener/v1/url', params=p)
        j = r.json()

        if 'error' not in j:
            return j['longUrl']
        else:
            raise ServiceError(j['error']['message'], r)


@_shortener('git.io')
class Gitio(Shortener):
    def shorten(self, url, custom=None):
        p = {'url': url, 'code': custom}
        r = requests.post('http://git.io', data=p)

        if r.status_code == requests.codes.created:
            s = r.headers['location']
            if custom and not custom in s:
                raise ServiceError('That URL is already in use', r)
            else:
                return s
        else:
            raise ServiceError(r.text, r)


@_pastebin('hastebin')
class Hastebin(Pastebin):
    def paste(self, data, ext):
        r = requests.post(HASTEBIN_SERVER + '/documents', data=data)
        j = r.json()

        if r.status_code is requests.codes.ok:
            return '{}/{}.{}'.format(HASTEBIN_SERVER, j['key'], ext)
        else:
            raise ServiceError(j['message'], r)


@_shortener("qx.lc")
class QxlcLinks(Shortener):
    def shorten(self, url, custom=None):
        # qx.lc doesn't support custom urls, so ignore custom
        server = "http://qx.lc"
        r = requests.post("{}/api/shorten".format(server), data={"url": url})

        if r.status_code != 200:
            raise ServiceError(r.text, r)
        else:
            return r.text


@_pastebin("qx.lc")
class QxlcPaste(Pastebin):
    def paste(self, text, ext):
        r = requests.post("http://qx.lc/api/paste", data={"paste": text})
        url = r.text

        if r.status_code != 200:
            return r.text  # this is the error text
        else:
            if ext is not None:
                return "{}.{}".format(url, ext)
            else:
                return url
