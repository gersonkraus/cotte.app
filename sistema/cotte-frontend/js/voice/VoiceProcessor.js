/**
 * VoiceProcessor.js
 * 
 * Gerencia a gravação de áudio via Blobs (para Whisper/STT no backend)
 * e a reprodução de áudio base64 (para TTS).
 */

const VoiceProcessor = (function() {
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let audioContext = null;
    let analyser = null;
    let dataArray = null;
    let animationFrame = null;

    return {
        isRecording: () => isRecording,

        /**
         * Inicia a gravação de áudio do microfone.
         */
        startRecording: async function() {
            if (isRecording) return;
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                // Visualizer Setup
                this.initVisualizer(stream);

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.start();
                isRecording = true;
                console.log("[VoiceProcessor] Gravação iniciada");
                return true;
            } catch (err) {
                console.error("[VoiceProcessor] Erro ao acessar microfone:", err);
                return false;
            }
        },

        initVisualizer: function(stream) {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(stream);
                analyser = audioContext.createAnalyser();
                analyser.fftSize = 32; // Pequeno para barras simples
                source.connect(analyser);

                const bufferLength = analyser.frequencyBinCount;
                dataArray = new Uint8Array(bufferLength);

                const bars = document.querySelectorAll('#voiceVisualizer .v-bar');
                if (bars.length === 0) return;

                const draw = () => {
                    if (!isRecording) return;
                    animationFrame = requestAnimationFrame(draw);
                    analyser.getByteFrequencyData(dataArray);

                    bars.forEach((bar, i) => {
                        // Mapeia o valor da frequência para altura (4px a 24px)
                        const val = dataArray[i % bufferLength] || 0;
                        const height = Math.max(4, (val / 255) * 24);
                        bar.style.height = `${height}px`;
                    });
                };
                draw();
            } catch (e) {
                console.warn("[VoiceProcessor] Falha ao iniciar visualizador:", e);
            }
        },

        /**
         * Para a gravação e retorna o Blob de áudio.
         */
        stopRecording: function() {
            return new Promise((resolve) => {
                if (!mediaRecorder || !isRecording) {
                    resolve(null);
                    return;
                }

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    isRecording = false;
                    
                    // Para todos os tracks do stream
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    
                    // Para o visualizador
                    if (animationFrame) cancelAnimationFrame(animationFrame);
                    if (audioContext) audioContext.close();
                    
                    console.log("[VoiceProcessor] Gravação finalizada, blob gerado:", audioBlob.size, "bytes");
                    resolve(audioBlob);
                };

                mediaRecorder.stop();
            });
        },

        /**
         * Converte um Blob para Base64.
         */
        blobToBase64: function(blob) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        },

        /**
         * Reproduz um áudio a partir de uma string base64.
         */
        playBase64Audio: function(base64Data, format = 'mpeg') {
            if (!base64Data) return;
            
            try {
                const audioSrc = `data:audio/${format};base64,${base64Data}`;
                const audio = new Audio(audioSrc);
                audio.play().catch(e => console.error("[VoiceProcessor] Erro ao reproduzir áudio:", e));
                return audio;
            } catch (err) {
                console.error("[VoiceProcessor] Erro ao preparar áudio:", err);
            }
        }
    };
})();

// Expõe globalmente
window.VoiceProcessor = VoiceProcessor;
