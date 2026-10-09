// Sequential report requests; benchmark invocations continue to use a fresh process.
import readline from 'node:readline';

export async function dispatch(run, args) {
  if (args[1] !== '--session') {
    await run(args);
    process.exit(0);
  }
  const write = process.stdout.write.bind(process.stdout);
  const directory = process.cwd();
  const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
  for await (const line of lines) {
    const request = JSON.parse(line);
    let diagnostic = '';
    process.stdout.write = (chunk, encoding, callback) => {
      if (typeof encoding === 'function') encoding();
      else if (callback) callback();
      return true;
    };
    process.stderr.write = (chunk, encoding, callback) => {
      diagnostic = (diagnostic + chunk.toString()).slice(-1800);
      if (typeof encoding === 'function') encoding();
      else if (callback) callback();
      return true;
    };
    let exitCode = 0;
    try {
      process.chdir(request.cwd);
      for (const [key, value] of Object.entries(request.env)) process.env[key] = value;
      await run([args[0], ...request.args]);
    } catch (error) {
      exitCode = 1;
      diagnostic = (diagnostic + (error.stack ?? String(error))).slice(-1800);
    } finally {
      process.chdir(directory);
    }
    write(JSON.stringify({id: request.id, exitCode, diagnostic}) + '\n');
  }
  process.exit(0);
}
