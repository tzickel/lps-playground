const PluginBridge = require('./pluginbridge');

var plugin = new PluginBridge('Demo NodeJS Launcher', '../python/metadata.json');

plugin.on('error', (e) => {
    console.log('plugin error', e);
});

plugin.on('stopped', () => {
    console.log('plugin stopped');
});

plugin.on('started', () => {
    console.log('plugin started');
    plugin.request('1 + 2');
    plugin.request('1 * -3');
    plugin.stop();
});

plugin.on('entriesadd', (entries) => {
    console.log('entriesadd', entries);
});

plugin.on('entriesfinished', (time) => {
    console.log('entriesfinished', time);
});

plugin.on('entriesremove', (ids) => {
    console.log('entriesremove', ids);
});

plugin.on('entriesremoveall', () => {
    console.log('entriesremoveall');
});

plugin.start();
