import express from 'express';
import cors from 'cors';
import { AgentInputItem, Runner, withTrace } from '@openai/agents';
import { guardrailsConfig, runAndApplyGuardrails, jeff, informer } from './agent';
import dotenv from 'dotenv';
dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 3000;

app.post('/chat', async (req, res) => {
    try {
        const { messages, mode } = req.body;
        
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            return res.status(400).json({ error: 'messages array is required' });
        }

        // Setup streaming headers
        res.setHeader('Content-Type', 'text/plain');
        res.setHeader('Transfer-Encoding', 'chunked');
        res.setHeader('Cache-Control', 'no-cache');

        await withTrace("Jeff Flagship Suite", async () => {
            const runner = new Runner({
                traceMetadata: {
                    __trace_source__: "agent-builder",
                    workflow_id: process.env.JEFF_WORKFLOW_ID
                }
            });

            // Extract the latest user message text
            const lastMessage = messages[messages.length - 1];
            let guardrailsInputText = "";
            if (lastMessage && lastMessage.content) {
                if (Array.isArray(lastMessage.content)) {
                    for (const part of lastMessage.content) {
                        if (part.type === "input_text") guardrailsInputText += part.text;
                    }
                } else if (typeof lastMessage.content === 'string') {
                    guardrailsInputText = lastMessage.content;
                }
            }

            const workflow = { input_as_text: guardrailsInputText };
            
            // 1. Guardrails check
            const { hasTripwire } = await runAndApplyGuardrails(guardrailsInputText, guardrailsConfig, messages, workflow);

            let activeAgent = jeff;
            if (hasTripwire) {
                activeAgent = informer;
            } else {
                // If it's Jeff, append the mode to the last message context to fulfill the requirement
                // Note: since it's the last message, modifying it instructs Jeff for this turn.
                if (Array.isArray(lastMessage.content)) {
                    const textPart = lastMessage.content.find((p: any) => p.type === 'input_text');
                    if (textPart) {
                        textPart.text = `[System Context: Respond in '${mode}' mode]\nUser Message: ${textPart.text}`;
                    }
                }
            }

            // 2. Stream execution
            const run = await runner.runStreamed(activeAgent, messages);
            
            for await (const chunk of run) {
                // Determine how `@openai/agents` emits text delta events
                if (chunk.type === 'messageDelta' && chunk.messageDelta?.content) {
                    for (const content of chunk.messageDelta.content) {
                        if (content.type === 'text_delta' && content.textDelta) {
                            res.write(content.textDelta);
                        }
                    }
                } else if (chunk.type === 'text_delta' && chunk.text_delta) {
                    res.write(chunk.text_delta);
                } else if (chunk.type === 'textDelta' && chunk.textDelta) {
                    res.write(chunk.textDelta);
                } else if (chunk.delta) { // fallback
                    if (typeof chunk.delta === 'string') {
                        res.write(chunk.delta);
                    } else if (chunk.delta.text) {
                        res.write(chunk.delta.text);
                    }
                }
            }

            const finalResult = await run.finalResult();
            const usage = finalResult?.usage || { prompt_tokens: 0, completion_tokens: 0 };
            res.write(`\n\n__USAGE__:${JSON.stringify(usage)}`);
        });
        
        res.end();
    } catch (err: any) {
        console.error("Error in /chat:", err);
        if (!res.headersSent) {
            res.status(500).json({ error: err.message || String(err) });
        } else {
            res.end();
        }
    }
});

app.listen(PORT, () => {
    console.log(`Node Agent Sidecar running on port ${PORT}`);
});
