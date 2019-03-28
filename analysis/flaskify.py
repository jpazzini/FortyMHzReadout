from flask import Flask, render_template
from bokeh.client import pull_session
from bokeh.embed import server_session

app = Flask(__name__)

@app.route('/', methods=['GET'])
def bkapp_page():
    with  pull_session(session_id='daq', url='http://10.64.22.10:5006/') as session:
    	script = server_session(None, session.id, url='http://10.64.22.10:5006/') 
    	print script
	return render_template("index.html", script=script, template="Flask")
if __name__ == '__main__':
    app.run(host='10.64.22.10', port=8000, debug=True)

