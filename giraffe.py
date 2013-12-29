import os
import StringIO
import tempfile

import boto
from boto.s3.key import Key
import PIL
from PIL import Image
from flask import Flask
from flask import request


# settings to tweak:
os.environ['AWS_ACCESS_KEY_ID'] = '' # AWS_ACCESS_KEY_ID
os.environ['AWS_SECRET_ACCESS_KEY'] = '' # AWS_SECRET_ACCESS_KEY
BUCKET = ''


#
app = Flask(__name__)
app.debug = True


s3 = None
bucket = None


def connect_s3():
    global s3, bucket
    if not s3:
        s3 = boto.connect_s3()
    if not bucket:
        bucket = s3.get_bucket(BUCKET)


@app.route("/")
def index():
    return "Hello World"


@app.route("/<path:path>")
def image_route(path):
    args = get_image_args(request.args)
    params = args.values()
    if params:
        print "we have params"
        key = bucket.get_key(path)
        if key:
            print "and the original path exists"
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
            custom_key = bucket.get_key(key_name)
            if custom_key:
                return custom_key.read(), 200, {"Content-Type": "image/jpeg"}
            else:
                img = Image.open(StringIO.StringIO(key.read()))
                size = min(args['w'], img.size[0]), min(args['h'], img.size[1])
                new_img = img.resize(size, PIL.Image.NEAREST)
                temp_handle = StringIO.StringIO()
                new_img.save(temp_handle, format='JPEG')

                new_key = Key(bucket)
                new_key.key = key_name

                temp_handle.seek(0)
                new_key.set_contents_from_string(temp_handle.read(), {"Content-Type": "image/jpeg"})

                temp_handle.seek(0)
                return temp_handle.read(), 200, {"Content-Type": "image/jpeg"}
        else:
            return "404: original file '{}' doesn't exist".format(path), 404
    else:
        return get_file_or_404(path)


def int_or_bust(value):
    try:
        return int(value)
    except ValueError:
        return None
    except TypeError:
        return None


def positive(value):
    if value >= 0:
        return value
    else:
        return None


def get_image_args(args):
    w = positive(int_or_bust(args.get("w")))
    h = positive(int_or_bust(args.get("h")))

    args = {}
    if w:
        args['w'] = w
    if h:
        args['h'] = h

    return args


def get_file_or_404(path):
    key = bucket.get_key(path)
    if key:
        return key.read(), 200, {"Content-Type": "image/jpeg"}
    else:
        return "404: file '{}' doesn't exist".format(path), 404



if __name__ == "__main__":
    connect_s3()
    app.run("0.0.0.0", 9876)
