# Training a Model

1. Decide the model you want to use.

    Each model has a different set of pros and cons that define the run-time efficiency and the voice quality. It is up to you to decide what model servers your needs. Other than referring to the papers, one easy way is to test the 🐸TTS
    community models and see how fast and good each of the models. Or you can start a discussion on our communication channels.

2. Understand the configuration, its fields and values.

    For instance, if you want to train a `Tacotron` model then see the `TacotronConfig` class and make sure you understand it.

3. Check the recipes.

    Recipes are located under `TTS/recipes/`. They do not promise perfect models but they provide a good start point for
    `Nervous Beginners`.
    A recipe for `GlowTTS` using `LJSpeech` dataset looks like below. Let's be creative and call this `train_glowtts.py`.

    ```python
    # train_glowtts.py

   import os

    from TTS.trainer import Trainer, TrainingArgs
    from TTS.tts.configs.shared_config import BaseDatasetConfig
    from TTS.tts.configs.glow_tts_config import GlowTTSConfig
    from TTS.tts.datasets import load_tts_samples
    from TTS.tts.models.glow_tts import GlowTTS
    from TTS.utils.audio import AudioProcessor

    output_path = os.path.dirname(os.path.abspath(__file__))
    dataset_config = BaseDatasetConfig(
        name="ljspeech", meta_file_train="metadata.csv", path=os.path.join(output_path, "../LJSpeech-1.1/")
    )
    config = GlowTTSConfig(
        batch_size=32,
        eval_batch_size=16,
        num_loader_workers=4,
        num_eval_loader_workers=4,
        run_eval=True,
        test_delay_epochs=-1,
        epochs=1000,
        text_cleaner="phoneme_cleaners",
        use_phonemes=True,
        phoneme_language="en-us",
        phoneme_cache_path=os.path.join(output_path, "phoneme_cache"),
        print_step=25,
        print_eval=False,
        mixed_precision=True,
        output_path=output_path,
        datasets=[dataset_config],
    )

    # init audio processor
    ap = AudioProcessor(**config.audio.to_dict())

    # load training samples
    train_samples, eval_samples = load_tts_samples(dataset_config, eval_split=True)

    # init model
    model = GlowTTS(config)

    # init the trainer and 🚀
    trainer = Trainer(
        TrainingArgs(),
        config,
        output_path,
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
        training_assets={"audio_processor": ap},
    )
    trainer.fit()

    ```

    You need to change fields of the `BaseDatasetConfig` to match your dataset and then update `GlowTTSConfig`
    fields as you need.

 4. Run the training.

    ```bash
    $ CUDA_VISIBLE_DEVICES="0" python train_glowtts.py
    ```

    Notice that we set the GPU for the training by `CUDA_VISIBLE_DEVICES` environment variable.
    To see available GPUs on your system, you can use `nvidia-smi` command on the terminal.

    If you like to run a multi-gpu training using DDP back-end,

    ```bash
    $ CUDA_VISIBLE_DEVICES="0, 1, 2" python TTS/bin/distribute.py --script <path_to_your_script>/train_glowtts.py
    ```

    The example above runs a multi-gpu training using GPUs `0, 1, 2`.

    Beginning of a training log looks like this:

    ```console
    > Experiment folder: /your/output_path/-Juni-23-2021_02+52-78899209
    > Using CUDA:  True
    > Number of GPUs:  1
    > Setting up Audio Processor...
    | > sample_rate:22050
    | > resample:False
    | > num_mels:80
    | > min_level_db:-100
    | > frame_shift_ms:None
    | > frame_length_ms:None
    | > ref_level_db:20
    | > fft_size:1024
    | > power:1.5
    | > preemphasis:0.0
    | > griffin_lim_iters:60
    | > signal_norm:True
    | > symmetric_norm:True
    | > mel_fmin:0
    | > mel_fmax:None
    | > spec_gain:20.0
    | > stft_pad_mode:reflect
    | > max_norm:4.0
    | > clip_norm:True
    | > do_trim_silence:True
    | > trim_db:45
    | > do_sound_norm:False
    | > stats_path:None
    | > base:10
    | > hop_length:256
    | > win_length:1024
    | > Found 13100 files in /your/dataset/path/ljspeech/LJSpeech-1.1
    > Using model: glow_tts

    > Model has 28356129 parameters

    > EPOCH: 0/1000

    > DataLoader initialization
    | > Use phonemes: False
    | > Number of instances : 12969
    | > Max length sequence: 187
    | > Min length sequence: 5
    | > Avg length sequence: 98.3403500655409
    | > Num. instances discarded by max-min (max=500, min=3) seq limits: 0
    | > Batch group size: 0.

    > TRAINING (2021-06-23 14:52:54)

    --> STEP: 0/405 -- GLOBAL_STEP: 0
        | > loss: 2.34670
        | > log_mle: 1.61872
        | > loss_dur: 0.72798
        | > align_error: 0.52744
        | > current_lr: 2.5e-07
        | > grad_norm: 5.036039352416992
        | > step_time: 5.8815
        | > loader_time: 0.0065
    ...
    ```

5. Run the Tensorboard.

    ```bash
    $ tensorboard --logdir=<path to your training directory>
    ```

6. Monitor the training process.

    On the terminal and Tensorboard, you can monitor the progress of your model. Also Tensorboard provides certain figures and sample outputs.

    Note that different models have different metrics, visuals and outputs.

    You should also check the [FAQ page](https://github.com/coqui-ai/TTS/wiki/FAQ) for common problems and solutions
    that occur in a training.

7. Use your best model for inference.

    Use `tts` or `tts-server` commands for testing your models.

    ```bash
    $ tts --text "Text for TTS" \
          --model_path path/to/checkpoint_x.pth.tar \
          --config_path path/to/config.json \
          --out_path folder/to/save/output.wav
    ```

8. Return to the step 1 and reiterate for training a `vocoder` model.

    In the example above, we trained a `GlowTTS` model, but the same workflow applies to all the other 🐸TTS models.


# Multi-speaker Training

Training a multi-speaker model is mostly the same as training a single-speaker model.
You need to specify a couple of configuration parameters, initiate a `SpeakerManager` instance and pass it to the model.

The configuration parameters define whether you want to train the model with a speaker-embedding layer or pre-computed
d-vectors. For using d-vectors, you first need to compute the d-vectors using the `SpeakerEncoder`.

The same Glow-TTS model above can be trained on a multi-speaker VCTK dataset with the script below.

```python
import os

from TTS.config.shared_configs import BaseAudioConfig
from TTS.trainer import Trainer, TrainingArgs
from TTS.tts import BaseDatasetConfig, GlowTTSConfig
from TTS.tts.datasets import load_tts_samples
from TTS.tts.glow_tts import GlowTTS
from TTS.tts.utils.speakers import SpeakerManager
from TTS.utils.audio import AudioProcessor

# define dataset config for VCTK
output_path = os.path.dirname(os.path.abspath(__file__))
dataset_config = BaseDatasetConfig(name="vctk", meta_file_train="", path=os.path.join(output_path, "../VCTK/"))

# init audio processing config
audio_config = BaseAudioConfig(sample_rate=22050, do_trim_silence=True, trim_db=23.0)

# init training config
config = GlowTTSConfig(
    batch_size=64,
    eval_batch_size=16,
    num_loader_workers=4,
    num_eval_loader_workers=4,
    run_eval=True,
    test_delay_epochs=-1,
    epochs=1000,
    text_cleaner="phoneme_cleaners",
    use_phonemes=True,
    phoneme_language="en-us",
    phoneme_cache_path=os.path.join(output_path, "phoneme_cache"),
    print_step=25,
    print_eval=False,
    mixed_precision=True,
    output_path=output_path,
    datasets=[dataset_config],
    use_speaker_embedding=True,
)

# init audio processor
ap = AudioProcessor(**config.audio.to_dict())

# load training samples
train_samples, eval_samples = load_tts_samples(dataset_config, eval_split=True)

# ONLY FOR MULTI-SPEAKER: init speaker manager for multi-speaker training
speaker_manager = SpeakerManager()
speaker_manager.set_speaker_ids_from_data(train_samples + eval_samples)
config.num_speakers = speaker_manager.num_speakers

# init model
model = GlowTTS(config, speaker_manager)

# init the trainer and 🚀
trainer = Trainer(
    TrainingArgs(),
    config,
    output_path,
    model=model,
    train_samples=train_samples,
    eval_samples=eval_samples,
    training_assets={"audio_processor": ap},
)
trainer.fit()
```
