from flask import Flask, render_template, request, jsonify
import paramiko
import os

app = Flask(__name__)


# === CONFIGURE YOUR VPS HOST AND SSH USER BELOW ===
VPS_HOST = 'IP_OR_DOMAIN'      # Your VPS IP address or DNS name
VPS_USER = 'root'              # SSH username (usually 'root' or 'ubuntu')
SSH_KEY_PATH = os.path.join(os.path.dirname(__file__), 'id_ed25519')  # Private key file name

def run_ssh_command(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_HOST, username=VPS_USER, key_filename=SSH_KEY_PATH)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    ssh.close()
    return output, error

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    cmd = "systemctl list-units --type=service --all --no-pager --no-legend"
    output, error = run_ssh_command(cmd)
    services = []
    for line in output.strip().split('\n'):
        line = line.strip()
        # Пропуск пустых и "точечных" строк
        if not line or line == '●':
            continue
        parts = line.split(None, 4)
        if len(parts) >= 5 and parts[0] != '●':
            services.append({
                'name': parts[0],
                'load': parts[1],
                'active': parts[2],
                'sub': parts[3],
                'description': parts[4]
            })
    return jsonify(services=services, error=error)

@app.route('/action', methods=['POST'])
def action():
    data = request.json
    service = data.get('service')
    action = data.get('action')
    if action not in ('start', 'stop', 'restart'):
        return jsonify({'error': 'Invalid action'})
    cmd = f"sudo systemctl {action} {service}"
    output, error = run_ssh_command(cmd)
    return jsonify({'output': output, 'error': error})

@app.route('/logs', methods=['POST'])
def logs():
    service_name = request.json.get('service_name', '')
    cmd = f"journalctl -u {service_name} -n 100 --no-pager"
    output, error = run_ssh_command(cmd)
    return jsonify(logs=output, error=error)

@app.route('/status_detail', methods=['POST'])
def status_detail():
    service_name = request.json.get('service_name', '')
    cmd = f"systemctl status {service_name} --no-pager"
    output, error = run_ssh_command(cmd)
    return jsonify(status=output, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0')