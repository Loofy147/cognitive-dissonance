import gradio as gr

def hello_world():
    return "Hello, World!"

iface = gr.Interface(fn=hello_world, inputs=None, outputs="text")
iface.launch()
