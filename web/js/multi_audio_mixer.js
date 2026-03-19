import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.MultiAudioMixer",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MultipleAudioUpload") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                const updateWidgets = () => {
                    const trackCountWidget = this.widgets.find(w => w.name === "track_count");
                    const trackCount = trackCountWidget ? trackCountWidget.value : 1;
                    
                    this.widgets.forEach(w => {
                        if (w.name === "track_count") return;

                        const match = w.name.match(/_(\d+)$/);
                        if (match) {
                            const trackNum = parseInt(match[1]);
                            const isVisible = trackNum <= trackCount;

                            if (!isVisible) {
                                // Ховаємо: зберігаємо старий тип, якщо ще не зберегли
                                if (w.type !== "hidden") {
                                    w._original_type = w.type;
                                    w.type = "hidden";
                                }
                            } else {
                                // Показуємо: повертаємо оригінальний тип
                                if (w.type === "hidden") {
                                    w.type = w._original_type || (w.name.startsWith("audio") ? "combo" : "number");
                                }
                            }
                            
                            // Додатково ховаємо DOM елементи, якщо вони є (важливо для кнопок завантаження)
                            if (w.inputEl) {
                                w.inputEl.style.display = isVisible ? "" : "none";
                            }
                        }
                    });

                    // Оновлюємо інтерфейс
                    this.setDirtyCanvas(true, true);
                };

                // Вішаємо обробник на зміну кількості треків
                const tcWidget = this.widgets.find(w => w.name === "track_count");
                if (tcWidget) {
                    tcWidget.callback = () => {
                        updateWidgets();
                    };
                }

                // Запуск при створенні з невеликою затримкою
                setTimeout(() => {
                    updateWidgets();
                    if (this.graph) {
                        this.setSize(this.computeSize());
                    }
                }, 50);

                return r;
            };
        }
    }
});