import { runWorkflow } from './agent';

async function main() {
    let input = '';
    for await (const chunk of process.stdin) {
        input += chunk;
    }
    
    try {
        const data = JSON.parse(input);
        const inputAsText = data.input_as_text;
        if (!inputAsText) {
            console.error(JSON.stringify({ error: "No input provided" }));
            process.exit(1);
        }
        const result = await runWorkflow({ input_as_text: inputAsText });
        console.log(JSON.stringify(result));
    } catch (err: any) {
        console.error(JSON.stringify({ error: err.message || String(err) }));
        process.exit(1);
    }
}

main();
