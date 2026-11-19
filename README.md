# Circle Survivors Live

Vertical browser game for YouTube Live with three modes: Shrinking Circle, Flag Collision Battle, and Comment & Photo Circle.

Open the GitHub Pages link for the game. For live comments, run `pip install -r requirements.txt` and `python chat_bridge.py` on the streaming computer. In the game settings, paste the YouTube live link and click **Connect Chat**. The bridge listens on `127.0.0.1:8765` and reads public live chat. The **Demo** button works without YouTube.

GitHub Pages hosts the game page only. The local chat bridge must remain running on the streaming computer; it is not hosted by GitHub Pages. OBS can use the Pages URL as a browser source.
