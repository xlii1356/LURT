const DEFAULT_REACTIONS = [
    {
        "ID": "brace",
        "Rank": "-",
        "Name": "Brace",
        "Trigger": "You are hit by an attack and damage has been rolled.",
        "Frequency": "1/round",
        "Detail": "You count as having RESISTANCE to all damage, burn, and heat from the triggering attack, and until the end of your next turn, all other attacks against you are made at +1 difficulty. Due to the stress of bracing, you cannot take reactions until the end of your next turn and on that turn, you can only take one quick action, you cannot OVERCHARGE, move normally, take full actions, or take free actions."
    },
    {
        "ID": "overwatch",
        "Rank": "-",
        "Name": "Overwatch",
        "Trigger": "A hostile character starts any movement (including BOOST and other actions) inside one of your weapons THREAT.",
        "Frequency": "1/round",
        "Detail": "Trigger OVERWATCH, immediately using that weapon to SKIRMISH against that character as a reaction, before they move."
    }
];

export class ReactionTracker extends Application {
    constructor(options = {}) {
        super(options);
        this.reactions = [];
        this.reactionData = []; // The raw CSV data
        this.currentTheme = game.settings.get("lurt", "theme") || "GMS";
        this._loadReactionData();

        // Initialize with defaults
        this.reactions = JSON.parse(JSON.stringify(DEFAULT_REACTIONS));
        this._initializeReactionState(this.reactions);
    }

    static get defaultOptions() {
        return mergeObject(super.defaultOptions, {
            id: "lurt-tracker",
            title: "Lancer Ultimate Reaction Tracker",
            template: "modules/lurt/templates/tracker.hbs",
            width: 820,
            height: 720,
            classes: ["lurt"],
            resizable: true
        });
    }

    async _loadReactionData() {
        try {
            const response = await fetch("modules/lurt/assets/lancer_reactions.json");
            this.reactionData = await response.json();
            // Process _min_rank like python
            this.reactionData.forEach(r => {
                let mr = r["min_talent_rank"] || r["Min Talent Rank"];
                let rank = 1;
                if (mr) {
                    // Try parsing int directly
                    const parsed = parseInt(mr);
                    if (!isNaN(parsed)) rank = parsed;
                    else {
                        // regex extract digit
                        const m = mr.match(/(\d+)/);
                        if (m) rank = parseInt(m[1]);
                    }
                }
                r._min_rank = rank;
            });

        } catch (e) {
            console.error("LURT | Failed to load reaction data", e);
            ui.notifications.error("LURT: Failed to load reaction database.");
        }
    }

    getData() {
        return {
            reactions: this.reactions,
            themes: ["GMS", "Horus", "MSMC", "Harrison Armory"].map(t => ({
                id: t,
                name: t,
                active: t === this.currentTheme
            })),
            themeClass: `theme-${this.currentTheme.toLowerCase().replace(/\s+/g, '-')}`
        };
    }

    activateListeners(html) {
        super.activateListeners(html);

        html.find(".theme-select").change(ev => {
            this.currentTheme = ev.target.value;
            game.settings.set("lurt", "theme", this.currentTheme);
            this.render();
        });

        html.find(".open-json").click(() => this._openJSONDialog());
        html.find(".next-round").click(() => this._resetRound());

        html.find(".use-reaction").click(ev => {
            const btn = $(ev.currentTarget);
            const id = btn.closest(".reaction-item").data("id");
            // Find index, using index in array or ID. ID might not be unique if duplicates allowed? 
            // Python used object references. Here `this.reactions` is the source of truth.
            // But handlebars doesn't give us index easily without helper.
            // We can trust the order or add a unique runtime ID.
            // Let's rely on data-index if we add it, or just find by property if ID is unique enough (it isn't).
            // Actually, the button is inside the item.
            const index = btn.closest(".reaction-item").index();
            this._useReaction(index);
        });
    }

    _openJSONDialog() {
        // Create a file input
        const input = $('<input type="file" accept=".json">');
        input.on("change", ev => {
            const file = ev.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = e => {
                try {
                    const json = JSON.parse(e.target.result);
                    this._processPilotData(json);
                } catch (err) {
                    ui.notifications.error("LURT: " + err.message);
                }
            };
            reader.readAsText(file);
        });
        input.trigger("click");
    }

    _processPilotData(data) {
        const comps = this._loadAllComponents(data);
        const matches = this._matchComponents(comps);
        //Sort matches
        matches.sort((a, b) => (a.Name || "").localeCompare(b.Name || "") || (a.ID || "").localeCompare(b.ID || ""));

        // Inject defaults
        const currentIds = new Set(matches.map(m => m.ID));
        for (const def of DEFAULT_REACTIONS) {
            if (!currentIds.has(def.ID)) {
                matches.unshift(JSON.parse(JSON.stringify(def)));
            }
        }

        this.reactions = matches;
        this._initializeReactionState(this.reactions);
        this.render();
    }

    _initializeReactionState(reactions) {
        reactions.forEach(r => {
            const [maxUses, resets] = this._parseFrequency(r.Frequency);
            r.maxUses = maxUses;
            r.resetsEachRound = resets;
            r.uses = 0;
            r.exhausted = false;
            r.usesCount = maxUses > 1 && maxUses !== Infinity;
        });
    }

    _parseFrequency(freq) {
        if (!freq) return [1, true];
        const s = String(freq).trim().toLowerCase();
        if (s.startsWith("unlimited")) return [Infinity, true];

        const m = s.match(/(\d+)\s*\/\s*round/);
        if (m) return [parseInt(m[1]), true];

        if (s.startsWith("1/scene") || s.startswith("1/mission")) return [1, false];
        return [1, true];
    }

    _useReaction(index) {
        const r = this.reactions[index];
        if (!r) return;

        r.uses++;

        if (r.maxUses === Infinity) {
            // Unlimited logic (flash 'Used')
            // Handle in UI render or specific update
            // We'll just re-render for now, though it might be jerky.
            // Ideally we just update DOM. 
        } else {
            if (r.uses >= r.maxUses) {
                r.exhausted = true;
            }
        }
        this.render();
    }

    _resetRound() {
        this.reactions.forEach(r => {
            if (r.resetsEachRound) {
                r.uses = 0;
                r.exhausted = false;
            }
        });
        this.render();
    }

    // --- Parsing Logic (Ported from Python) ---

    _normalize(s) {
        if (!s) return "";
        return String(s).toLowerCase().replace(/[^a-z0-9]/g, "");
    }

    _extractIds(obj, collected) {
        if (typeof obj === "object" && obj !== null) {
            if (Array.isArray(obj)) {
                obj.forEach(i => this._extractIds(i, collected));
            } else {
                if ("id" in obj) {
                    let rank = obj.rank;
                    if (typeof rank !== "number") {
                        if (Array.isArray(obj.ranks)) {
                            rank = obj.ranks.reduce((max, r) => Math.max(max, r.tier || 0), 1);
                        } else {
                            rank = 1;
                        }
                    }
                    collected.push({ id: obj.id, rank: rank, raw: obj });
                }
                Object.values(obj).forEach(v => this._extractIds(v, collected));
            }
        }
    }

    _loadAllComponents(data) {
        const collected = [];
        const pilotKeys = ["talents", "traits", "core_bonuses"];

        // Pilot Data
        pilotKeys.forEach(k => {
            if (data[k]) this._extractIds(data[k], collected);
        });
        if (data.pilot) {
            pilotKeys.forEach(k => {
                if (data.pilot[k]) this._extractIds(data.pilot[k], collected);
            });
        }

        // Active Mech
        let activeId = data.state?.active_mech_id;
        let mechs = data.mechs || [];
        let activeMech = null;

        if (!Array.isArray(mechs) && typeof mechs === 'object') {
            // Dictionary format
            activeMech = mechs[activeId];
        } else if (Array.isArray(mechs)) {
            activeMech = mechs.find(m => String(m.id) === String(activeId));
        }

        if (activeMech) {
            // Frame
            if (activeMech.frame) {
                const fid = typeof activeMech.frame === 'string' ? activeMech.frame : activeMech.frame.id;
                if (fid) collected.push({ id: fid, rank: 3, raw: {} });
            }

            // Loadouts
            let loadouts = activeMech.loadouts || [];
            if (!Array.isArray(loadouts)) loadouts = Object.values(loadouts);

            loadouts.forEach(ld => {
                if (!ld) return;
                // Systems
                let systems = ld.systems || [];
                if (!Array.isArray(systems)) systems = Object.values(systems);
                systems.forEach(s => {
                    const sid = (typeof s === 'string') ? s : s.id;
                    if (sid) collected.push({ id: sid, rank: 3, raw: {} });
                });

                // Mounts / Integrated
                const allMounts = [];
                let mStd = ld.mounts || [];
                if (!Array.isArray(mStd)) mStd = Object.values(mStd);
                allMounts.push(...mStd);

                let mInt = ld.integratedMounts || [];
                if (!Array.isArray(mInt)) mInt = Object.values(mInt);
                allMounts.push(...mInt);

                allMounts.forEach(mount => {
                    if (!mount) return;
                    const slotsToCheck = [];

                    let sList = mount.slots || [];
                    if (!Array.isArray(sList)) sList = Object.values(sList);
                    slotsToCheck.push(...sList);

                    let eList = mount.extra || [];
                    if (!Array.isArray(eList)) eList = Object.values(eList);
                    slotsToCheck.push(...eList);

                    slotsToCheck.forEach(slot => {
                        if (!slot) return;
                        // Weapon obj
                        if (slot.weapon && typeof slot.weapon === 'object' && slot.weapon.id) {
                            collected.push({ id: slot.weapon.id, rank: 3, raw: slot.weapon });
                            return;
                        }
                        if (typeof slot.weapon === 'string' && slot.weapon) {
                            collected.push({ id: slot.weapon, rank: 3, raw: {} });
                            return;
                        }
                        // Fallbacks
                        if (slot.item) collected.push({ id: slot.item, rank: 3, raw: {} });
                        else if (slot.id && typeof slot.id === 'string') collected.push({ id: slot.id, rank: 3, raw: {} });
                        else if (slot.weapon_id) collected.push({ id: slot.weapon_id, rank: 3, raw: {} });
                    });
                });
            });
        }

        // Merge and Count
        const merged = {};
        collected.forEach(it => {
            const key = this._normalize(it.id);
            if (!key) return;
            if (!merged[key]) merged[key] = { id: it.id, rank: 0, count: 0 };

            merged[key].rank = Math.max(merged[key].rank, it.rank || 1);
            merged[key].count += 1;
        });

        return Object.values(merged);
    }

    _matchComponents(components) {
        const results = [];
        const byPid = {};

        // Index CSV data by Parent ID
        this.reactionData.forEach(r => {
            const pid = this._normalize(r["Parent_ID"] || r["ParentID"] || r["Parent_Id"] || "");
            if (!byPid[pid]) byPid[pid] = [];
            byPid[pid].push(r);
        });

        components.forEach(comp => {
            const pid = this._normalize(comp.id);
            if (!pid) return;

            const candidates = byPid[pid] || [];
            candidates.forEach(r => {
                if ((comp.rank || 1) >= (r._min_rank || 1)) {
                    // Frequency Scaling
                    let freqStr = (r["Frequency"] || "").trim();
                    const count = comp.count || 1;

                    if (count > 1 && freqStr && !freqStr.toLowerCase().includes("unlimited")) {
                        const m = freqStr.match(/^(\d+)(.*)/);
                        if (m) {
                            const baseUses = parseInt(m[1]);
                            const newUses = baseUses + (count - 1);
                            freqStr = `${newUses}${m[2]}`;
                        }
                    }

                    results.push({
                        ID: comp.id,
                        Rank: comp.rank,
                        Name: (r["Name"] || "").trim(),
                        Trigger: (r["Trigger"] || "").trim(),
                        Frequency: freqStr,
                        Detail: (r["Detail"] || "").trim()
                    });
                }
            });
        });
        return results;
    }
}
