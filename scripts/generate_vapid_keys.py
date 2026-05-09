#!/usr/bin/env python3
"""Run once to generate VAPID key pair. Add output to your .env file."""
from py_vapid import Vapid

v = Vapid()
v.generate_keys()
public_key = v.public_key_b64.decode()
private_key = v.private_key_b64.decode()
print(f'VAPID_PUBLIC_KEY={public_key}')
print(f'VAPID_PRIVATE_KEY={private_key}')
print('VAPID_EMAIL=info@powaynec.com')
print()
print('Add the above 3 lines to your .env file, then restart the Flask server.')
