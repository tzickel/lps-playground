const { spawn } = require('child_process');
const rpc = require('vscode-jsonrpc');
const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');


module.exports = class PluginBridge extends EventEmitter {
    constructor(name, metadataPath) {
        super();
		this.name = name;
		this.metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
		this.metadataDir = path.dirname(path.resolve(metadataPath));
		this.runtimes = null;
		this.connection = null;
		this.client = null;
		this.client_name = null;
    }

    get information() {
        return this.metadata['information'];
    }

	_trynextruntime() {
		if (this.runtimes === null) {
			return;
		}
		this.client = null;
		let iter = this.runtimes.next();
		if (iter.done) {
			this.runtimes = null;
			this.emit('error', new Error(this.metadata['runtime']['errorMessage'] || 'Could not run plugin'));
		} else {
			let runtime = iter.value;
			// TODO should we run it as a shell ?
			let client = spawn(runtime[0], runtime.slice(1), {
				cwd: this.metadataDir
			});

			client.on('error', (err) => {
				this._trynextruntime();
			});

			client.on('exit', (code, signal) => {
				if (this.client) {
					this.connection = null;
					this.client = null;
					this.client_name = null;
					this.emit('stopped', code || signal);
				} else {
					this._trynextruntime();
				}
			});

			let connection = rpc.createMessageConnection(
				new rpc.StreamMessageReader(client.stdout),
				new rpc.StreamMessageWriter(client.stdin));

			// TODO which events should I hook on connection for errors 

			connection.onNotification('helloclient', (name, apiversion) => {
				this.runtimes = null;
				this.connection = connection;
				this.client = client;
				this.client_name = name;
				this.emit('started');
			})

			connection.onNotification('error', (method, message) => {
				console.log('error', method, message);
			});

			connection.onNotification('entriesadd', (entries) => {
				this.emit('entriesadd', entries);
			});

			connection.onNotification('entriesfinished', (id) => {
				let end = new Date();
				this.emit('entriesfinished', id, end - this.request_start_time);
			});

			connection.onNotification('entriesremove', (ids) => {
				this.emit('entriesremove', ids);
			});

			connection.onNotification('entriesremoveall', () => {
				this.emit('entriesremoveall');
			});

			connection.onNotification((method) => {
				connection.sendNotification('error', method, 'Unknown method');
			});
			
			connection.listen();

			connection.sendNotification('helloserver', {
				'name': this.name,
				'apiversions': ['v0.1']
			});
		}
	}

    start() {
		if (this.runtimes !== null) {
			return;
		}

		let runtime = this.metadata['runtime']['command'];
		if (!Array.isArray(runtime[0])) {
			runtime = [runtime];
		}

		this.runtimes = runtime[Symbol.iterator]();

		this._trynextruntime();
	}

	stop(force = false) {
		if (this.connection) {
			this.connection.sendNotification('shutdown');
		}
		if (force) {
			this.connection.stop();
			this.client.stop();
		}
	}

	request(id, text) {
		this.request_start_time = new Date();
		this.connection.sendNotification('request', { 'id': id, 'text': text });
	}
}
