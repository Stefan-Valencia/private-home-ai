# Private Home AI Appliance

A local-first home AI appliance designed to make private, on-device AI as simple to set up as a home router.

## MVP goals

- Set up from a phone through a temporary appliance Wi-Fi network and browser-based wizard.
- Generate the appliance identity during customer setup and require a physical action to authorize trusted devices.
- Configure the home's Wi-Fi, then use the appliance from a phone or computer browser.
- Run local AI inference and local document question answering without a mandatory cloud account.

## Project status

The repository now contains three clearly labeled software-only prototypes: first-boot setup, an in-memory device-pairing lifecycle, and a local AI chat/document service. They do not control physical devices, create real device credentials, or make production security claims. The target appliance must be validated separately.

The current hardware evaluation target is an AMD Ryzen AI Max+ 395 system with 128 GB unified memory. Hardware compatibility, model speed, thermals, network setup, recovery, and security behavior remain to be verified on the selected device.

## Scope

The initial MVP focuses on local-network setup and use. Secure remote access, fleet management, enterprise multi-user permissions, and cloud inference are later decisions.

See the project brief and roadmap for requirements and milestones.

## Local AI software prototype

The browser chat, local inference adapter, bounded specialist delegation, local document index, citations, and privacy limits are in [assistant/README.md](assistant/README.md). The prototype expects a local OpenAI-compatible model server and does not include model weights. Its document search is lexical keyword retrieval, not semantic embeddings.

## License

The repository includes CC0 1.0 Universal in LICENSE. Model weights, datasets, and third-party dependencies have separate license terms.

## Run the onboarding simulation

Run the simulation locally on this computer with `python -m http.server 4173 --bind 127.0.0.1`. Open `http://127.0.0.1:4173` in its browser. The setup flow and device-management screen are simulations only: they do not enable Wi-Fi, authenticate or pair devices, create credentials, or accept network credentials. After finishing the setup walkthrough, choose **Explore device management simulation** to try a temporary demo window, add or remove synthetic devices, see expiry and retry behavior, and reset the in-memory demo state. Refreshing the page clears that state.

Run the state-machine checks with `node --test`.
