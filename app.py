import gradio as gr
from implementation.answer import answer_question

def format_context(context_docs):
    result = "<h2 style='color: #ff7800;'>Użyty kontekst</h2>\n\n"
    for doc in context_docs:
        result += f"<span style='color: #ff7800;'>Source: {doc.metadata['source']}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result

def chat(history):
    last_message = history[-1]["content"]
    # Gradio może zwracać różne formaty: string, lista, lub słownik {'text': ..., 'type': ...}
    if isinstance(last_message, dict):
        last_message = last_message.get("text", "")
    elif isinstance(last_message, list):
        last_message = " ".join(str(x) for x in last_message)
    prior = history[:-1]
    answer, context = answer_question(last_message, prior)
    history.append({"role": "assistant", "content": answer})
    return history, format_context(context)

def main():
    def put_message_in_chatbot(message, history):
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Asystant sklepu NeoGadżet") as ui:
        gr.Markdown("# 🏢 Asystant sklepu NeoGadżet\nZapytaj mnie o cokolwiek z NeoGadżet!")

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="💬 Konwersacja", height=600
                )
                message = gr.Textbox(
                    label="Twoje pytanie",
                    placeholder="Zapytaj o cokolwiek z NeoGadżet...",
                    show_label=False,
                )

            with gr.Column(scale=1):
                context_markdown = gr.Markdown(
                    label="📚 Pobrany kontekst",
                    value="*Pojawi się tu pobrany kontekst*",
                    container=True,
                    height=600,
                )

        message.submit(
            put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True, theme=theme)


if __name__ == "__main__":
    main()