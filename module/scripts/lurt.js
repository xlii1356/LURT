import { ReactionTracker } from "./reaction-tracker.js";

Hooks.once("init", () => {
    console.log("LURT | Initializing Lancer Ultimate Reaction Tracker");

    // Register module settings if needed
    game.settings.register("lurt", "theme", {
        name: "Default Theme",
        scope: "client",
        config: true,
        type: String,
        choices: {
            "GMS": "GMS",
            "Horus": "Horus",
            "MSMC": "MSMC",
            "Harrison Armory": "Harrison Armory"
        },
        default: "GMS",
        onChange: () => {
            if (ui.lurt) ui.lurt.render();
        }
    });
});

Hooks.on("getSceneControlButtons", (controls) => {
    const tokenControls = controls.find(c => c.name === "token");
    if (tokenControls) {
        tokenControls.tools.push({
            name: "lurt",
            title: "Open Reaction Tracker",
            icon: "fas fa-shield-alt",
            onClick: () => {
                if (!ui.lurt) {
                    ui.lurt = new ReactionTracker();
                }
                ui.lurt.render(true);
            },
            button: true
        });
    }
});
