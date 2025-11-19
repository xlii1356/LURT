import tkinter as tk
from tkinter import ttk, filedialog
import json


class ReactionApp:
    def __init__(self, root):


        self.root = root
        self.root.title("Reaction Manager")
        self.reactions = []

        custom_font = ("Arial", 10)  # Define your font (family, size, style)
        self.root.option_add("*Font", custom_font)  # Apply the font globally

        self.control_frame = ttk.Frame(root)
        self.control_frame.pack(side='left', fill='y', padx=10, pady=10)

        self.add_reaction_button = ttk.Button(self.control_frame, text="Add Reaction", command=self.add_reaction)
        self.add_reaction_button.pack(fill='x', pady=5)

        self.new_round_button = ttk.Button(self.control_frame, text="New Round", command=self.reset_reactions)
        self.new_round_button.pack(fill='x', pady=5)

        self.save_button = ttk.Button(self.control_frame, text="Save Reactions", command=self.save_reactions)
        self.save_button.pack(fill='x', pady=5)

        self.load_button = ttk.Button(self.control_frame, text="Load Reactions", command=self.load_reactions)
        self.load_button.pack(fill='x', pady=5)

        # Main display area for reactions
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(side='right', fill='both', expand=True)

        self.canvas = tk.Canvas(self.main_frame)
        self.h_scrollbar = ttk.Scrollbar(self.main_frame, orient='horizontal', command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self.main_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.v_scrollbar.pack(side="right", fill="y")

        # Add predefined reactions
        self.add_reaction(name="Overwatch", trigger="A hostile character starts any movement (including BOOST and other actions) inside one of your weapons’ THREAT.", effect="Immediately use that weapon to SKIRMISH against that character as a reaction, before they move.")
        self.add_reaction(name="Brace", trigger="You are hit by an attack and damage has been rolled", effect="You count as having RESISTANCE to all damage, burn, and heat from the triggering attack, and until the end of your next turn, all other attacks against you are made at +1 difficulty. Due to the stress of bracing, you cannot take reactions until the end of your next turn and on that turn, you can only take one quick action – you cannot OVERCHARGE, move normally, take full actions, or take free actions.")

    def add_reaction(self, name="", trigger="", effect="", used=False, one_per_scene=False):
        reaction_frame = ttk.Frame(self.scrollable_frame, relief='solid', borderwidth=1, padding=10)

        name_label = ttk.Label(reaction_frame, text="Name:")
        name_label.grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(reaction_frame, width=25)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        name_entry.insert(0, name)

        # Trigger Field
        trigger_label = ttk.Label(reaction_frame, text="Trigger:")
        trigger_label.grid(row=1, column=0, padx=5, pady=5)
        trigger_text = tk.Text(reaction_frame, width=30, height=3, wrap="word", relief="solid", borderwidth=1)
        trigger_scroll = ttk.Scrollbar(reaction_frame, orient='vertical', command=trigger_text.yview)
        trigger_text.configure(yscrollcommand=trigger_scroll.set)
        trigger_text.grid(row=1, column=1, padx=5, pady=5)
        trigger_scroll.grid(row=1, column=2, sticky="ns")
        trigger_text.insert(1.0, trigger)

        # Bind the <<Modified>> event to dynamically resize the Trigger field
        trigger_text.bind("<<Modified>>", lambda e, widget=trigger_text: self.auto_resize_textbox(widget))

        # Effect Field
        effect_label = ttk.Label(reaction_frame, text="Effect:")
        effect_label.grid(row=2, column=0, padx=5, pady=5)
        effect_text = tk.Text(reaction_frame, width=30, height=3, wrap="word", relief="solid", borderwidth=1)
        effect_scroll = ttk.Scrollbar(reaction_frame, orient='vertical', command=effect_text.yview)
        effect_text.configure(yscrollcommand=effect_scroll.set)
        effect_text.grid(row=2, column=1, padx=5, pady=5)
        effect_scroll.grid(row=2, column=2, sticky="ns")
        effect_text.insert(2.0, effect)

        # Bind the <<Modified>> event to dynamically resize the Effect field
        effect_text.bind("<<Modified>>", lambda e, widget=effect_text: self.auto_resize_textbox(widget))

        one_per_scene_var = tk.BooleanVar(value=one_per_scene)
        one_per_scene_check = ttk.Checkbutton(reaction_frame, text="1/Scene?", variable=one_per_scene_var)
        one_per_scene_check.grid(row=3, column=0, padx=5, pady=5)

        use_button = ttk.Button(reaction_frame, text="Use", command=lambda: self.use_reaction(reaction_frame))
        use_button.grid(row=3, column=1, padx=5, pady=5)

        remove_button = ttk.Button(reaction_frame, text="Remove", command=lambda: self.remove_reaction(reaction_frame))
        remove_button.grid(row=3, column=2, padx=5, pady=5)

        if used:
            self.use_reaction(reaction_frame)


        # Store reaction data
        self.reactions.append((reaction_frame, name_entry, trigger_text, effect_text, use_button, one_per_scene_var))

        # Re-layout the reactions
        self.layout_reactions()

    def remove_reaction(self, reaction_frame):
       # Find and remove the reaction from the list
       for i, (frame, _, _, _, _, _) in enumerate(self.reactions):
           if frame == reaction_frame:
               self.reactions.pop(i)
               frame.destroy()
               break


       # Re-layout the reactions
       self.layout_reactions()    

    def use_reaction(self, reaction_frame):
        # Loop through all child widgets of the reaction frame
        for widget in reaction_frame.winfo_children():
            if isinstance(widget, tk.Text):
                widget.config(state=tk.DISABLED)  # Disable the Text widget
            else:
                widget.state(['disabled'])  # Disable other widgets (like Entry, Button, etc.)

        reaction_frame.configure(style='UsedReaction.TFrame')  # Change the style to indicate it's used


    def reset_reactions(self):
        for reaction_frame, name_entry, trigger_entry, effect_entry, use_button, one_per_scene_var in self.reactions:
            if not one_per_scene_var.get():  # Check if it's a one-per-scene reaction
                for widget in reaction_frame.winfo_children():
                    if isinstance(widget, tk.Text):
                        widget.config(state=tk.NORMAL)  # Re-enable the Text widget
                    else:
                        widget.state(['!disabled'])  # Re-enable other widgets (like Entry, Button, etc.)
                reaction_frame.configure(style='Reaction.TFrame')  # Reset the style to normal


    def save_reactions(self):
        reaction_data = []
        for _, name_entry, trigger_entry, effect_entry, use_button, one_per_scene_var in self.reactions:
            reaction_data.append({
                "name": name_entry.get(),
                "trigger": trigger_entry.get("1.0", "end").strip(),  # Use .get() with the correct arguments
                "effect": effect_entry.get("1.0", "end").strip(),    # Same for effect_entry
                "used": False,
                "one_per_scene": one_per_scene_var.get()
            })
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(reaction_data, f)


    def load_reactions(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                reaction_data = json.load(f)
            self.reset_reactions()
            for reaction in self.reactions:
                reaction[0].destroy()
            self.reactions.clear()
            for reaction_info in reaction_data:
                self.add_reaction(
                    reaction_info['name'],
                    reaction_info['trigger'],
                    reaction_info['effect'],
                    reaction_info['used'],
                    reaction_info.get('one_per_scene', False)
                )

    def layout_reactions(self):
        # Clear all reactions from the grid
        for reaction_frame, _, _, _, _, _ in self.reactions:
            reaction_frame.grid_forget()

        # Re-layout reactions
        for index, (reaction_frame, _, _, _, _, _) in enumerate(self.reactions):
            row, column = divmod(index, 3)  # Adjust the number of columns per row here
            reaction_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")

    def auto_resize_textbox(self, widget):
        # Check if the content has changed
        if widget.edit_modified():
            # Get the content and widget width
            content = widget.get("1.0", "end").strip()
            widget_width = int(widget.cget("width"))

            # Calculate the total number of visible lines, considering wrapping
            wrapped_lines = sum((len(line) // widget_width) + 1 for line in content.split("\n"))
            num_lines = max(3, wrapped_lines)  # Minimum height is 3 lines

            # Adjust the height of the Text widget
            widget.configure(height=min(10, num_lines))  # Maximum height is 10 lines

            # Reset the modified flag
            widget.edit_modified(False)
   


if __name__ == "__main__":
    root = tk.Tk()

    style = ttk.Style()
    style.configure('Reaction.TFrame', background='white')
    style.configure('UsedReaction.TFrame', background='grey')

    app = ReactionApp(root)
    root.mainloop()
