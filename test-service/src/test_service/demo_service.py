import connexion
from datetime import datetime
import os
import traceback
from six.moves.urllib.request import urlopen
import json
from jose import jwt
from flask import _request_ctx_stack


SPECIFICATION_DIR = os.getenv('SPECIFICATION_DIR', './')
AUTH0_DOMAIN = 'dev-y0ottw4e.auth0.com'
API_AUDIENCE = 'http://localhost:5000'
ALGORITHMS = ["RS256"]


def get_utc_timestamp(with_decimal: bool=False): 
    epoch = datetime(1970,1,1,0,0,0) 
    now = datetime.utcnow() 
    timestamp = (now - epoch).total_seconds() 
    if with_decimal: 
        return timestamp 
    return int(timestamp) 


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


class CertCache:

    def __init__(self):
        self.cert = None
        self.cert_expires = 0

    def _refresh_cert(self):
        try:
            print('CertCache: refreshing JWKS')
            jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
            self.cert = json.loads(jsonurl.read())
            self.cert_expires = get_utc_timestamp(with_decimal=False) + 3600
        except:
            print('EXCEPTION: {}'.format(traceback.format_exc()))

    def get_cert(self):
        now = get_utc_timestamp(with_decimal=False)
        if now > self.cert_expires:
            self._refresh_cert()
        return self.cert


cert_cache = CertCache()


def decode_token(token):
    payload = dict()
    try:
        # return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
        # jwks = json.loads(jsonurl.read())
        jwks = cert_cache.get_cert()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_AUDIENCE,
                    issuer="https://"+AUTH0_DOMAIN+"/"
                )
            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired",
                                "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims",
                                "description":
                                    "incorrect claims,"
                                    "please check the audience and issuer"}, 401)
            except Exception:
                raise AuthError({"code": "invalid_header",
                                "description":
                                    "Unable to parse authentication"
                                    " token."}, 401)

            _request_ctx_stack.top.current_user = payload
        raise AuthError({"code": "invalid_header",
                        "description": "Unable to find appropriate key"}, 401)
    except:
        print('EXCEPTION: {}'.format(traceback.format_exc()))
    return payload


def readiness():
    return { 'timestamp': get_utc_timestamp(with_decimal=False) }, 200


def user_profile_get(token_info):
    print('token_info={}'.format(token_info))
    machine_client_id = token_info['sub']
    authorization_type = token_info['gty']
    return { 'machineClientId': machine_client_id, 'authorizationType': authorization_type }, 200


options = {"swagger_ui": False}
if int(os.getenv('SWAGGER_UI', '1')) > 0:
    options = {"swagger_ui": True}    
app = connexion.FlaskApp(__name__, specification_dir=SPECIFICATION_DIR)
app.add_api('demo-service.yaml', strict_validation=True)


def run():
    app.run(port=5000)

if __name__ == '__main__':
    run()




# EOF
