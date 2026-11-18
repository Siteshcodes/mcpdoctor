(() => {
  function initialize() {
    const form = document.getElementById('command-builder');
    if (!form || form.dataset.ready) return;
    form.dataset.ready = 'true';
    const mode = document.getElementById('command-mode');
    const shell = document.getElementById('command-shell');
    const target = document.getElementById('command-target');
    const output = document.getElementById('generated-command');
    const thorough = document.getElementById('command-thorough');
    const ascii = document.getElementById('command-ascii');
    const status = document.getElementById('copy-status');
    function update() {
      const value = target.value.trim();
      const isChat = mode.value === 'chat';
      const valid = value.length > 0 && !/[\r\n]/.test(value);
      target.setCustomValidity(valid ? '' : 'Enter one server path or launch command.');
      document.getElementById('audit-options').hidden = isChat;
      const escaped = shell.value === 'powershell'
        ? value.replace(/'/g, "''")
        : value.replace(/'/g, "'\"'\"'");
      const flags = isChat ? '' : `${thorough.checked ? ' --thorough' : ''}${ascii.checked ? ' --ascii' : ''}`;
      output.textContent = valid ? `uv run mcpdoctor ${mode.value} '${escaped}'${flags}` : 'Enter a server path or launch command above.';
      document.querySelector('[data-copy="generated-command"]').disabled = !valid;
      document.getElementById('builder-note').textContent = isChat
        ? 'Chat requires GROQ_API_KEY. Tool calls and repair retries execute on your server.'
        : 'Run on trusted development servers and disposable data. Active probes execute requests.';
      status.textContent = '';
    }
    form.addEventListener('submit', event => event.preventDefault());
    form.addEventListener('input', update);
    form.addEventListener('change', update);
    document.querySelectorAll('[data-copy]').forEach(button => {
      button.addEventListener('click', async () => {
        const text = document.getElementById(button.dataset.copy).textContent;
        try {
          await navigator.clipboard.writeText(text);
          status.textContent = 'Command copied. Paste it into your terminal.';
          const label = button.textContent;
          button.textContent = 'Copied!';
          setTimeout(() => { button.textContent = label; }, 1800);
        } catch {
          status.textContent = 'Clipboard unavailable. Select and copy the command above.';
        }
      });
    });
    update();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
