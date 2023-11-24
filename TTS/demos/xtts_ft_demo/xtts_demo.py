import os
import sys
import tempfile

import gradio as gr
import librosa.display
import numpy as np

import os
import torch
import torchaudio
from TTS.demos.xtts_ft_demo.utils.formatter import format_audio_list, list_audios
from TTS.demos.xtts_ft_demo.utils.gpt_train import train_gpt

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts


PORT = 5003

def load_model(xtts_checkpoint, xtts_config, xtts_vocab):
    config = XttsConfig()
    config.load_json(xtts_config)
    model = Xtts.init_from_config(config)
    print("Loading XTTS model! ")
    model.load_checkpoint(config, checkpoint_path=xtts_checkpoint, vocab_path=xtts_vocab, use_deepspeed=False)
    if torch.cuda.is_available():
        model.cuda()
    return model

def run_tts(lang, tts_text, xtts_checkpoint, xtts_config, xtts_vocab, speaker_audio_file):
    # ToDo: add the load in other function to fast inference
    model = load_model(xtts_checkpoint, xtts_config, xtts_vocab)
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=speaker_audio_file, gpt_cond_len=model.config.gpt_cond_len, max_ref_length=model.config.max_ref_len, sound_norm_refs=model.config.sound_norm_refs)
    speaker_embedding
    out = model.inference(
        text=tts_text,
        language=lang,
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
        temperature=model.config.temperature, # Add custom parameters here
        length_penalty=model.config.length_penalty,
        repetition_penalty=model.config.repetition_penalty,
        top_k=model.config.top_k,
        top_p=model.config.top_p,
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp:
        out["wav"] = torch.tensor(out["wav"]).unsqueeze(0)
        out_path = fp.name
        torchaudio.save(out_path, out["wav"], 24000)

    return out_path, speaker_audio_file




# define a logger to redirect 
class Logger:
    def __init__(self, filename="log.out"):
        self.log_file = filename
        self.terminal = sys.stdout
        self.log = open(self.log_file, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def isatty(self):
        return False

# redirect stdout and stderr to a file
sys.stdout = Logger()
sys.stderr = sys.stdout


# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def read_logs():
    sys.stdout.flush()
    with open(sys.stdout.log_file, "r") as f:
        return f.read()


with gr.Blocks() as demo:
    # state_vars = gr.State()
    with gr.Tab("Data processing"):    
        upload_file = gr.Audio(
            sources="upload",
            label="Select here the audio files that you want to use for XTTS trainining !",
            type="filepath",
        )
        lang = gr.Dropdown(
            label="Dataset Language",
            value="en",
            choices=[
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "pl",
                "tr",
                "ru",
                "nl",
                "cs",
                "ar",
                "zh",
                "hu",
                "ko",
                "ja"
            ],
        )
        progress_data = gr.Label(
            label="Progress:"
        )
        logs = gr.Textbox(
            label="Logs:",
            interactive=False,
        )
        demo.load(read_logs, None, logs, every=1)

        prompt_compute_btn = gr.Button(value="Step 1 - Create dataset.")
    
        def preprocess_dataset(audio_path, language, progress=gr.Progress(track_tqdm=True)):
            # create a temp directory to save the dataset
            out_path = tempfile.TemporaryDirectory().name
            if audio_path is None:
                # ToDo: raise an error
                pass
            else:
                train_meta, eval_meta = format_audio_list([audio_path], target_language=language, out_path=out_path, gradio_progress=progress)

            return "Dataset Processed!", train_meta, eval_meta

    with gr.Tab("Fine-tuning XTTS"):
        train_csv = gr.Textbox(
            label="Train CSV:",
        )
        eval_csv = gr.Textbox(
            label="Eval CSV:",
        )
        num_epochs =  gr.Slider(
            label="num_epochs",
            minimum=1,
            maximum=100,
            step=1,
            value=2,# 15
        )
        batch_size = gr.Slider(
            label="batch_size",
            minimum=2,
            maximum=512,
            step=1,
            value=15,
        )
        progress_train = gr.Label(
            label="Progress:"
        )
        logs_tts_train = gr.Textbox(
            label="Logs:",
            interactive=False,
        )
        demo.load(read_logs, None, logs_tts_train, every=1)
        train_btn = gr.Button(value="Step 2 - Run the training")

        def train_model(language, train_csv, eval_csv, num_epochs, batch_size, output_path="./", progress=gr.Progress(track_tqdm=True)):
            # train_csv = '/tmp/tmprh4k_vou/metadata_train.csv'
            # eval_csv = '/tmp/tmprh4k_vou/metadata_eval.csv'

            config_path, original_xtts_checkpoint, vocab_file, exp_path, speaker_wav = train_gpt(language, num_epochs, batch_size, train_csv, eval_csv, output_path=output_path)
            # copy original files to avoid parameters changes issues
            os.system(f"cp {config_path} {exp_path}")
            os.system(f"cp {vocab_file} {exp_path}")

            ft_xtts_checkpoint = os.path.join(exp_path, "best_model.pth")
            # state_vars["config_path"] = config_path
            # state_vars["original_xtts_checkpoint"] = original_xtts_checkpoint
            # state_vars["vocab_file"] = vocab_file
            # state_vars["ft_xtts_checkpoint"] = ft_xtts_checkpoint
            # state_vars["speaker_audio_file"] = speaker_wav
            return "Model training done!", config_path, vocab_file, ft_xtts_checkpoint, speaker_wav


    with gr.Tab("Inference"):
        xtts_checkpoint = gr.Textbox(
            label="XTTS checkpoint path:",
            value="",
        )
        xtts_config = gr.Textbox(
            label="XTTS config path:",
            value="",
        )
        xtts_vocab = gr.Textbox(
            label="XTTS config path:",
            value="",
        )
        speaker_reference_audio = gr.Textbox(
            label="Speaker reference audio:",
            value="",
        )
        tts_language = gr.Dropdown(
            label="Language",
            value="en",
            choices=[
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "pl",
                "tr",
                "ru",
                "nl",
                "cs",
                "ar",
                "zh",
                "hu",
                "ko",
                "ja",
            ]
        )
        tts_text = gr.Textbox(
            label="Input Text.",
            value="This model sounds really good and above all, it's reasonably fast.",
        )
        tts_btn = gr.Button(value="Step 3 - Inference XTTS model")

        tts_output_audio = gr.Audio(label="Generated Audio.")
        reference_audio = gr.Audio(label="Reference audio used.")

        prompt_compute_btn.click(
            fn=preprocess_dataset,
            inputs=[
                upload_file,
                lang,
            ],
            outputs=[
                progress_data,
                train_csv,
                eval_csv,
            ],
        )
        


        train_btn.click(
            fn=train_model,
            inputs=[
                lang,
                train_csv,
                eval_csv,
                num_epochs,
                batch_size,
            ],
            outputs=[progress_train, xtts_config, xtts_vocab, xtts_checkpoint, speaker_reference_audio],
        )
        

        tts_btn.click(
            fn=run_tts,
            inputs=[
                tts_language,
                tts_text,
                xtts_checkpoint,
                xtts_config,
                xtts_vocab,
                speaker_reference_audio,
            ],
            outputs=[tts_output_audio, reference_audio],
        )



if __name__ == "__main__":
    demo.launch(
        share=True,
        debug=True,
        server_port=PORT,
        server_name="0.0.0.0"
    )