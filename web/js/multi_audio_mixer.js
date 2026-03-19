import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "Comfy.MultiAudioMixer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "MultipleAudioUpload") {
            
            // Кольори для 5 логічних блоків
            const trackColors = [
                "rgba(46, 74, 61, 0.5)", // Track 1
                "rgba(61, 74, 46, 0.5)", // Track 2
                "rgba(46, 61, 74, 0.5)", // Track 3
                "rgba(74, 46, 69, 0.5)", // Track 4
                "rgba(74, 61, 46, 0.5)"  // Track 5
            ];

            nodeType.prototype.onNodeCreated = function() {
                this.setSize([400, 780]);
            };

            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function(ctx) {
                onDrawForeground?.apply(this, arguments);
                if (!this.widgets) return;

                // Кількість віджетів на один трек (Label, Vol, Bal, Start, Stop, Indent)
                // Примітка: Audio вхід — це не віджет, а слот, тому рахуємо текстові та числові поля
                const widgetsPerTrack = 6; 
                
                for (let i = 0; i < 5; i++) {
                    const isConnected = this.inputs[i]?.link !== null;
                    
                    // Вираховуємо стартовий індекс віджетів для кожного треку
                    // Перший віджет (index 0) — це track_count, далі йдуть групи
                    const startIdx = 1 + (i * widgetsPerTrack);
                    const trackWidgets = this.widgets.slice(startIdx, startIdx + widgetsPerTrack);

                    trackWidgets.forEach((w, idx) => {
                        if (!w.element && !w.canvas) return;

                        const targetEl = w.element || ctx.canvas; // Для стандартних віджетів Comfy

                        if (isConnected) {
                            // Активний трек: підсвічуємо фон та ставимо повну яскравість
                            if (w.element) {
                                w.element.style.backgroundColor = trackColors[i];
                                w.element.style.opacity = "1";
                                w.element.style.borderLeft = "4px solid #00ff00";
                            }
                            // Підсвічуємо текст самого лейбла (перший віджет у групі)
                            if (idx === 0) w.color = "#00ff00"; 
                        } else {
                            // Неактивний трек: приглушуємо
                            if (w.element) {
                                w.element.style.backgroundColor = "transparent";
                                w.element.style.opacity = "0.3";
                                w.element.style.borderLeft = "4px solid transparent";
                            }
                            if (idx === 0) w.color = "#666";
                        }
                    });
                }
            };
        }
    }
});