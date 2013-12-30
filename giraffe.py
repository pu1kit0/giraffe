from __future__ import absolute_import
from __future__ import print_function

import os
from io import BytesIO

import PIL
from PIL import Image
from flask import Flask
from flask import request
from requests.exceptions import HTTPError
import tinys3


"""
You'll need to set these environment variables:

 - AWS_ACCESS_KEY_ID
 - AWS_SECRET_ACCESS_KEY
 - GIRAFFE_BUCKET

I'd recommend setting them in your ``app.sh`` file.

"""

#
app = Flask(__name__)
app.debug = True


s3 = None
bucket = None


def connect_s3():
    global s3, bucket
    if not bucket:
        bucket = os.environ.get("GIRAFFE_BUCKET")
    if not s3:
        s3 = tinys3.Connection(os.environ.get("AWS_ACCESS_KEY_ID"),
                               os.environ.get("AWS_SECRET_ACCESS_KEY"),
                               default_bucket=bucket)
    return s3


@app.route("/")
def index():
    return "Hello World"


@app.route("/<path:path>")
def image_route(path):
    args = get_image_args(request.args)
    params = args.values()
    if params:
        return get_file_with_params_or_404(path, args)
    else:
        return get_file_or_404(path)


def positive_int_or_none(value):
    try:
        value = int(value)
        if value >= 0:
            return value
        else:
            return None
    except ValueError:
        return None
    except TypeError:
        return None


def get_image_args(args):
    w = positive_int_or_none(args.get("w"))
    h = positive_int_or_none(args.get("h"))

    args = {}
    if w:
        args['w'] = w
    if h:
        args['h'] = h

    return args


def get_object_or_none(path):
    try:
        obj = s3.get(path)
    except HTTPError as error:
        if error.response.status_code == 404:
            return None
        else:
            raise
    return obj


def get_file_or_404(path):
    key = get_object_or_none(path)
    if key:
        return key.content, 200, {"Content-Type": "image/jpeg"}
    else:
        return "404: file '{}' doesn't exist".format(path), 404


def get_file_with_params_or_404(path, args):
    print("we have params")
    key = get_object_or_none(path)
    if key:
        print("and the original path exists")
        dirname = os.path.dirname(path)
        name = os.path.basename(path)
        try:
            base, ext = name.split(".")
        except:
            return "no extension specified", 404
        stuff = [base,]
        stuff.extend(args.values())
        filename_with_args = "_".join(str(x) for x in stuff
                                   if x is not None) + "." + ext
        key_name = os.path.join('cache', dirname, filename_with_args)
        custom_key = get_object_or_none(key_name)
        if custom_key:
            return custom_key.content, 200, {"Content-Type": "image/jpeg"}
        else:
            img = Image.open(BytesIO(key.content))
            size = min(args.get('w', img.size[0]), img.size[0]), min(args.get('h', img.size[1]), img.size[1])
            if size != img.size:
                new_img = img.resize(size, PIL.Image.NEAREST)
                temp_handle = BytesIO()
                new_img.save(temp_handle, format='JPEG')
                s3.upload(key_name, temp_handle, content_type="image/jpeg", rewind=True, public=True)
                temp_handle.seek(0)
                return temp_handle.read(), 200, {"Content-Type": "image/jpeg"}
            else:
                return key.content, 200, {"Content-Type": "image/jpeg"}
    else: 
        return "404: original file '{}' doesn't exist".format(path), 404


if __name__ == "__main__":
    connect_s3()
    app.run("0.0.0.0", 9876)
