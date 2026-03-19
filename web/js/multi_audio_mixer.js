import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.MultiAudioMixer",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MultipleAudioUpload") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // Знаходимо віджет вибору кількості треків
                const trackCountWidget = this.widgets.find((w) => w.name === "track_count");
                
                const updateWidgets = () => {
                    const count = trackCountWidget.value;
                    
                    // Проходимо по всіх віджетах ноди
                    this.widgets.forEach((w) => {
                        // Ігноруємо сам track_count
                        if (w.name === "track_count") return;

                        // Витягуємо номер треку з назви віджета (наприклад, audio_1 -> 1)
                        const match = w.name.match(/_(\[0-9\]+)$/);
                        if (match) {
                            const trackNum = parseInt(match[1]);
                            // Якщо номер треку більший за вибраний count — ховаємо
                            if (trackNum > count) {
                                w.type = "hidden";
                            } else {
                                // Повертаємо тип віджета (це трохи "брудний" хак для Comfy, 
                                // але він працює для динамічного приховування)
                                if (w.name.startsWith("audio")) w.type = "AUDIO";
                                if (w.name.startsWith("volume") || w.name.startsWith("balance") || 
                                    w.name.startsWith("start") || w.name.startsWith("stop") || 
                                    w.name.startsWith("indent")) {
                                    w.type = "number";
                                }
                            }
                        }
                    });
                    
                    // Оновлюємо розмір ноди, щоб не було порожнього місця
                    this.setSize(this.computeSize());
                };

                // Вішаємо колбек на зміну значення
                trackCountWidget.callback = updateWidgets;

                // Запускаємо один раз при створенні
                setTimeout(updateWidgets, 10);

                return r;
            };
        }
    },
});