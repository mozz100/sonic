from flask import Flask, render_template, Blueprint, jsonify, redirect
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute
import os
import datetime
from flask_pynamodb_resource import create_resource

IS_OFFLINE = bool(os.environ.get("IS_OFFLINE", False))

class ShortCodeModel(Model):
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
    return render_template('index.html')

@app.route("/thanks")
def thanks():
    return render_template('thanks.html')

@app.route("/<code>")
def hit(code):
    try:
        code = ShortCodeModel.get(code)
        code.viewed = datetime.datetime.now().isoformat()
        code.save()
        code.refresh(consistent_read=True)
    except ShortCodeModel.DoesNotExist:
        # do redirect anyway
        pass
    return redirect("./thanks", code=302)
    

# See https://github.com/brandond/flask-pynamodb-resource/blob/master/examples/office_model.py
# Attach APIs to a blueprint to avoid cluttering up the root URL prefix
api_v1 = Blueprint('api_v1', __name__)

# Create the resources and register them with the blueprint
# Also override the endpoint name for each resource; by default it simply uses the model's table name
create_resource(ShortCodeModel).register(api_v1, '/codes')

@api_v1.route('/groups/<group_id>')
def group(group_id):
    # all codes in the group
    codes = [dict(s) for s in ShortCodeModel.scan(filter_condition=ShortCodeModel.group==group_id)]
    return jsonify(codes)

# Register the blueprint with the app AFTER attaching the resources
app.register_blueprint(api_v1, url_prefix='/api/v1')

if IS_OFFLINE:
    # Print rules to stdout
    for rule in app.url_map.iter_rules():
        print('{} => {}'.format(rule.rule, rule.endpoint))

if __name__ == "__main__":
    app.run()
