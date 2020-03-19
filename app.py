import datetime
import os

from flask import Blueprint, Flask, jsonify, render_template
from flask_pynamodb_resource import create_resource
from flask_restx import Api, Resource
from pynamodb.attributes import UnicodeAttribute
from pynamodb.models import Model

IS_OFFLINE = bool(os.environ.get("IS_OFFLINE", False))


class ShortCode(Model):
    class Meta:
        table_name = os.environ["TABLE_NAME"]
        if IS_OFFLINE:
            host = "http://localhost:8000"
        else:
            region = os.environ["REGION"]

    group = UnicodeAttribute()
    viewed = UnicodeAttribute(null=True)
    code = UnicodeAttribute(hash_key=True)

    def __iter__(self):
        for name, attr in self._get_attributes().items():
            yield name, attr.serialize(getattr(self, name))


app = Flask(__name__)


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/<code>")
def hit(code):
    try:
        code = ShortCode.get(code)
        code.viewed = datetime.datetime.now().isoformat()
        code.save()
        return render_template("thanks.html")
    except ShortCode.DoesNotExist:
        pass
    return render_template("miss.html"), 404


# See https://github.com/brandond/flask-pynamodb-resource/blob/master/examples/office_model.py
# Attach APIs to a blueprint to avoid cluttering up the root URL prefix
api_bp = Blueprint("api_v1", __name__)
api = Api(api_bp, default="Group", default_label="Groups", doc="/doc")

# Create the resources and register them with the blueprint
# Also override the endpoint name for each resource; by default it simply uses the model's table name
create_resource(ShortCode).register(api, "/codes")


@api.route("/groups/<id>")
@api.param("id", _in="path")
class Group(Resource):
    def get(self, id):
        codes = [
            dict(s) for s in ShortCode.scan(filter_condition=ShortCode.group == id)
        ]
        return codes


# Register the blueprint with the app AFTER attaching the resources
app.register_blueprint(api_bp, url_prefix="/api/v1")

if IS_OFFLINE:
    # Print routes to stdout
    for rule in app.url_map.iter_rules():
        print("{} => {}".format(rule.rule, rule.endpoint))

if __name__ == "__main__":
    app.run()
