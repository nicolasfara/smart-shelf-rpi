# smart-shelf-rpi
Smart shelf

## Install
For install all the dependencies:

```bash
export CFLAGS=-fcommon
source venv/bin/activate
pip install -r requirements.txt
```
For launching the app from _venv_:
```python
python smart-shelf.py
```
Note: for a successfully connection to AWS, create a .env file with the following vars pointing to AWS certificates:
```
AWS_ENDPOINT=xxxxxxxxxxx-ats.iot.eu-west-1.amazonaws.com
AWS_ROOT_CA=cert/AmazonRootCA1.pem
AWS_CERT=cert/xxxxxxxxx-certificate.pem.crt
AWS_KEY=cert/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-private.pem.key
CLIENT_ID=test-1234567
```
or set that vars as environment variable.

