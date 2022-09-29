from flask import Flask, render_template, request, jsonify
import subprocess
import queue
import signal
import sys, platform


action_queue = queue.PriorityQueue(1000) # 优先队列
app = Flask(__name__)

cmd = {
    "damage": False,
    "loss": False,
    "timeout": False
}

@app.route("/action/put", methods=["POST"])
def action_put():
    json_data = request.get_json()
    print((json_data["time"], json_data))
    action_queue.put((json_data["time"], json_data))

    return jsonify({"state":"ok"})

@app.route("/action/get", methods=["GET"])
def action_get():
    if not action_queue.empty():
        ret = action_queue.get(block=False)[1]
        return jsonify([ret, ])
    else:
        return jsonify(list())

@app.route("/cmd/get", methods=["GET"])
def cmd_get():
    field = request.args.get("field")
    return "true" if cmd[field] else "false"

@app.route("/cmd/set", methods=["GET"])
def cmd_set():
    field = request.args.get("field")
    value = request.args.get("value")
    if field not in cmd.keys():
        return "false"
    if value == "true":
        cmd[field] = True
        return "True"
    elif value == "false":
        cmd[field] = False
        return "true"
    return "false"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

def signal_handler(signum, frame):
    print('signal_handler: caught signal ' + str(signum))
    if signum == signal.SIGINT.value:
        p_sender.kill()
        p_receiver.kill()
        p_channel.kill()
        sys.exit(1)

def prepare():
    global p_sender
    global p_receiver
    global p_channel

    python_cmd = "python3"
    if platform.system() == "Linux":
        python_cmd = "python3"
    elif platform.system() == "Windows":
        python_cmd = "python"
        
    p_channel = subprocess.Popen([python_cmd,"channel.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p_receiver = subprocess.Popen([python_cmd, "sender.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p_sender = subprocess.Popen([python_cmd, "receiver.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    signal.signal(signal.SIGINT, signal_handler)

def main():
    prepare()
    app.run(host="127.0.0.1", port=8080)

if __name__ == "__main__":
    main()