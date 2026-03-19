import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.MultiAudioMixer",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MultipleAudioUpload") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                const self = this;

                const updateWidgets = () => {
                    const trackCountWidget = self.widgets.find(w => w.name === "track_count");
                    const trackCount = trackCountWidget ? trackCountWidget.value : 1;
                    
                    self.widgets.forEach(w => {
                        if (w.name === "track_count") return;

                        const match = w.name.match(/_(\d+)$/);
                        if (match) {
                            const trackNum = parseInt(match[1]);
                            const isVisible = trackNum <= trackCount;

                            if (!isVisible) {
                                if (w.type !== "hidden") {
                                    w._original_type = w.type;
                                    w.type = "hidden";
                                }
                            } else {
                                if (w.type === "hidden") {
                                    w.type = w._original_type || (w.name.startsWith("audio") ? "combo" : "number");
                                }
                            }
                            
                            if (w.inputEl) {
                                w.inputEl.style.display = isVisible ? "" : "none";
                            }
                        }
                    });

                    // Авто-корекція розміру ноди
                    const size = self.computeSize();
                    self.setSize([self.size[0], size[1]]);
                    app.graph.setDirtyCanvas(true, true);
                };

                // Прив'язка до зміни значення
                const tcWidget = self.widgets.find(w => w.name === "track_count");
                if (tcWidget) {
                    tcWidget.callback = updateWidgets;
                }

                // Викликаємо декілька разів з різною затримкою для надійності
                setTimeout(updateWidgets, 1);
                setTimeout(updateWidgets, 100);
                
                return r;
            };

            // Додаємо хук для перемальовування після завантаження
            nodeType.prototype.onAdded = function() {
                if (this.widgets) {
                    const trackCountWidget = this.widgets.find(w => w.name === "track_count");
                    if (trackCountWidget && trackCountWidget.callback) {
                        trackCountWidget.callback();
                    }
                }
            };
        }
    }
});