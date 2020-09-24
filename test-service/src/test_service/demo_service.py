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
            print('CertCache._refresh_cert(): refreshing JWKS')
            jsonurl = urlopen('https://{}/.well-known/jwks.json'.format(AUTH0_DOMAIN))
            self.cert = json.loads(jsonurl.read())
            self.cert_expires = get_utc_timestamp(with_decimal=False) + 3600
            print('CertCache._refresh_cert(): cert_expires={}'.format(self.cert_expires))
        except:
            print('EXCEPTION: {}'.format(traceback.format_exc()))

    def get_cert(self):
        now = get_utc_timestamp(with_decimal=False)
        if now > self.cert_expires:
            print('CertCache.get_cert(): Refressing JWKS')
            self._refresh_cert()
        else:
            print('CertCache.get_cert(): Using Cached JWKS')
        return self.cert


cert_cache = CertCache()


def decode_token(token):
    print('decode_token(): token={}'.format(token))
    payload = dict()
    error = None
    try:
        jwks = cert_cache.get_cert()
        #print('decode_token(): jwks={}'.format(jwks))
        unverified_header = jwt.get_unverified_header(token)
        print('decode_token(): unverified_header["kid"]={}'.format(unverified_header["kid"]))
        rsa_key = {}
        for key in jwks["keys"]:
            #print('decode_token(): key={}'.format(key))
            print('decode_token(): key["kid"]={}'.format(key['kid']))
            if key["kid"] == unverified_header["kid"]:
                print('decode_token(): MATCHING kid')
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                #print('decode_token(): rsa_key={}'.format(rsa_key))
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
                error = AuthError({"code": "token_expired", "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                error = AuthError({"code": "invalid_claims", "description": "incorrect claims, please check the audience and issuer"}, 401)
            except Exception:
                error = AuthError({"code": "invalid_header", "description": "Unable to parse authentication token."}, 401)
            _request_ctx_stack.top.current_user = payload
        else:
            raise AuthError({"code": "invalid_header", "description": "Unable to find appropriate key"}, 401)
    except:
        print('EXCEPTION: {}'.format(traceback.format_exc()))
    if error is not None:
        return error
    return payload


def readiness():
    return { 'timestamp': get_utc_timestamp(with_decimal=False) }, 200


def user_profile_get(token_info):
    print('token_info={}'.format(token_info))
    if 'sub' not in token_info or 'gty' not in token_info:
        return 'unauthorized', 401
    machine_client_id = token_info['sub']
    authorization_type = token_info['gty']
    return { 'machineClientId': machine_client_id, 'authorizationType': authorization_type }, 200


options = {"swagger_ui": False}
if int(os.getenv('SWAGGER_UI', '0')) > 0:
    options = {"swagger_ui": True}    
app = connexion.FlaskApp(__name__, specification_dir=SPECIFICATION_DIR)
app.add_api('demo-service.yaml', strict_validation=True)


def run():
    app.run(port=5000)

if __name__ == '__main__':
    run()




# EOF
