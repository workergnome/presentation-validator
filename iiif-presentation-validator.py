#!/usr/bin/env python
# encoding: utf-8
"""IIIF Presentation Validation Service"""

import argparse
import json
import os
import sys
try:
    # python3
    from urllib.request import urlopen, HTTPError
    from urllib.parse import urlparse
except ImportError:
    # fall back to python2
    from urllib2 import urlopen, HTTPError
    from urlparse import urlparse

from bottle import Bottle, abort, request, response, run

egg_cache = "/path/to/web/egg_cache"
os.environ['PYTHON_EGG_CACHE'] = egg_cache

from iiif_prezi.loader import ManifestReader


class Validator(object):

    def fetch(self, url):
        # print url
        try:
            wh = urlopen(url)
        except HTTPError as wh:
            pass
        data = wh.read()
        wh.close()
        return (data, wh)

    def format_response(self, data):
        response.content_type = "application/json"
        return json.dumps(data)

    def do_POST_test(self):
        data = request.json
        version = '2.0'
        warnings = []

        # Now check data
        reader = ManifestReader(data, version=version)
        err = None
        try:
            mf = reader.read()
            mf.toJSON()
            # Passed!
            okay = 1
        except Exception as err:
            # Failed
            okay = 0

        warnings.extend(reader.get_warnings())
        infojson = {'received': data, 'okay': okay, 'warnings': warnings, 'error': str(err)}
        return self.format_response(infojson)


    def do_GET_test(self):
        url = request.query.get('url', '')
        version = request.query.get('version', '2.0')

        url = url.strip()

        parsed_url = urlparse(url)
        if not parsed_url.scheme.startswith('http'):
            return self.format_response({'okay': 0, 'error': 'URLs must use HTTP or HTTPS', 'url': url})

        try:
            (data, webhandle) = self.fetch(url)
        except:
            return self.format_response({'okay': 0, 'error': 'Cannot fetch url', 'url': url})

        # First check HTTP level
        ct = webhandle.headers.get('content-type', '')
        cors = webhandle.headers.get('access-control-allow-origin', '')

        warnings = []
        if not ct.startswith('application/json') and not ct.startswith('application/ld+json'):
            # not json
            warnings.append("URL does not have correct content-type header: got \"%s\", expected JSON" % ct)
        if cors != "*":
            warnings.append("URL does not have correct access-control-allow-origin header:"
                            " got \"%s\", expected *" % cors)

        # Now check data
        reader = ManifestReader(data, version=version)
        err = None
        try:
            mf = reader.read()
            mf.toJSON()
            # Passed!
            okay = 1
        except Exception as err:
            # Failed
            okay = 0

        warnings.extend(reader.get_warnings())
        infojson = {'url': url, 'okay': okay, 'warnings': warnings, 'error': str(err)}
        return self.format_response(infojson)

    def index_route(self):
        resp = []
        fh = file(os.path.join(os.path.dirname(__file__),'head.html'))
        data = fh.read()
        fh.close()
        resp.append(data)

        fh = file(os.path.join(os.path.dirname(__file__),'index.html'))
        data = fh.read()
        fh.close()
        resp.append(data)

        fh = file(os.path.join(os.path.dirname(__file__),'foot.html'))
        data = fh.read()
        fh.close()
        resp.append(data)

        return ''.join(resp)


    def dispatch_views(self):
        self.app.route("/", "GET", self.index_route)
        self.app.route("/validate", "GET", self.do_GET_test)
        self.app.route("/validate", "POST", self.do_POST_test)

    def after_request(self):
        methods = 'GET'
        headers = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = methods
        response.headers['Access-Control-Allow-Headers'] = headers
        response.headers['Allow'] = methods

    def not_implemented(self, *args, **kwargs):
        """Returns not implemented status."""
        abort(501)

    def empty_response(self, *args, **kwargs):
        """Empty response"""

    options_list = empty_response
    options_detail = empty_response

    def error(self, error, message=None):
        """Returns the error response."""
        return self._jsonify({"error": error.status_code,
                              "message": error.body or message}, "")

    def get_bottle_app(self):
        """Returns bottle instance"""
        self.app = Bottle()
        self.dispatch_views()
        self.app.hook('after_request')(self.after_request)
        return self.app


def apache():
    v = Validator()
    return v.get_bottle_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip(),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--hostname', default='localhost',
                        help='Hostname or IP address to bind to (use 0.0.0.0 for all)')
    parser.add_argument('--port', default=8080, type=int,
                        help='Server port to bind to. Values below 1024 require root privileges.')

    args = parser.parse_args()

    v = Validator()
    run(host=args.hostname, port=args.port, app=v.get_bottle_app())

if __name__ == "__main__":
    main()
else:
    application = apache()
