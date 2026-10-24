# Private Home AI software-in-loop prototype

This prototype demonstrates local browser chat, one-prompt tool selection, read-only specialist delegation, bounded follow-up questions using temporary page-only context, and question answering over local `.txt` and text-based `.pdf` files. Home status is synthetic. It cannot discover or control physical devices.

## Start the prototype

Requirements: Python 3.12 or newer, a local `llama.cpp` server build, and a compatible GGUF chat model that you have permission to use.

1. Create and activate a Python environment from this directory, then install the app:

   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -e .
   ```

   On Linux, use `python3.12 -m venv .venv` and `source .venv/bin/activate` instead.

2. In a second terminal, start `llama-server` with your model. Replace the example path with the local model file you already obtained:

   ```powershell
   llama-server.exe -m C:\models\your-model.gguf --host 127.0.0.1 --port 8080 --alias local-model
   ```

   On Linux, use `llama-server -m /path/to/your-model.gguf --host 127.0.0.1 --port 8080 --alias local-model`. The local server must expose the OpenAI-compatible `/v1` API. Do not bind it to `0.0.0.0`.

   See the [official llama.cpp server guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) for supported builds and model-specific options.

3. In the first terminal, start the app:

   ```sh
   python -m home_ai.server
   ```

4. Open the local address printed at startup. The app and inference server bind to loopback and have no cloud fallback. If the model is still loading, use **Check again** in the page.

The project does not bundle or download a model. Model weights have their own licenses, sizes, and hardware requirements. The final model and inference backend remain open until the target computer is benchmarked.

## Evaluate the synthetic task set

From this directory, run the retrieval baseline without starting a model:

```sh
python -m home_ai.evaluate --retrieval-only
```

To evaluate routing, citations, abstention, prompt-injection resistance, and response time, first start the loopback-only model server as above, then run:

```sh
python -m home_ai.evaluate
```

The runner uses 20 synthetic documents and 40 fixed requests. It reports per-case pass indicators and summary metrics without printing the prompts or model answers. It uses the same loopback endpoint validation and no-proxy client as the app, and never falls back to a remote model. Use `--limit N` for a shorter sample or `--timeout-seconds N` to bound each request; a partial sample reports unmeasured quality gates as incomplete. Model-specific quality results still need to be collected; the deterministic retrieval baseline alone does not measure model answer quality.

## Privacy and limits

- The browser keeps up to five prior user/assistant text turns in page memory for follow-up questions. The **New chat** button and page refresh clear this history; it is not written to browser storage, the server session, or the document index.
- Prompts and retrieved passages go only to an IP loopback model endpoint. HTTP proxy environment variables are ignored, health checks do not follow redirects, and remote inference endpoints are rejected.
- The browser API accepts only its exact local host and same-origin requests. Do not expose either service to the home network; trusted-device authentication and network access are later milestones.
- Documents are indexed in a local SQLite database under the operating system's per-user data folder by default. On POSIX systems, the app restricts the data folder to owner-only access and the database to owner read/write. On Windows, the data folder inherits its Windows account permissions.
- The SQLite index is plaintext and is not encrypted at rest. Use synthetic or non-sensitive documents on a shared or untrusted computer; storage encryption and recovery are later milestones.
- Use **Remove** to delete a document's extracted text from the local index. The prototype does not retain a separate copy of the uploaded source file.
- Retrieval is local keyword search (SQLite FTS5), not semantic embeddings. Answers should cite `[filename, p. N]`; verify important details against the source.
- Uploads are limited to 10 MiB, 100 PDF pages, 2 MiB of decoded page content per page, 8 MiB across the whole PDF, and 500,000 extracted characters. Only UTF-8 text and selectable-text PDFs are supported. Scanned files, OCR, encrypted PDFs, and office documents are not supported.
- Incomplete HTTP request bodies have a ten-second total read deadline so a stalled upload cannot hold server shutdown indefinitely.
- Model output and document contents are untrusted. The available tools are limited to document search and simulated home status; no shell, internet, or device-control tools are exposed.
- This remains a software-in-loop prototype. Pairing, access-point setup, storage encryption, signed updates, recovery, model performance, and real-phone usability have not been validated on the target appliance.

## Local checks

From this directory:

```sh
python -m unittest discover -s tests -v
```

The tests use synthetic documents and deterministic fake models. They do not download model weights or make inference requests.
