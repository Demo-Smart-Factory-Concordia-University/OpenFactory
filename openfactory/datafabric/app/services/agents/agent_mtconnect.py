import requests
from flask_login import login_required
from openfactory.datafabric.app.services import bp


@bp.route('/mtc')
@login_required
def agent_mtconnect():
    r = requests.get('http://egegpu.encs.concordia.ca:3001')
    # r = requests.get('http://concordia.ca')
    # print(r.content.decode())
    return str(r)
