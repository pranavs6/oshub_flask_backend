### Functionality
1. **Toxicity Detection**: Checks for any means of toxicity in a given string, reports/stores the user/content based on the decision
2. **Cloud SQL Storage**: Adds all the data to GCP's Cloud SQL database for a search agent
3. **Search Functionality**: Returns a set of posts based on a search query

### To-Do
1. **Clone Celadon**:
   ```bash
   git-lfs clone https://huggingface.co/PleIAs/celadon
   ```
   For more information on installation, refer to the [Toxic Commons installation guide](https://github.com/Pleias/toxic-commons?tab=readme-ov-file#installation).
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the server**:
   ```bash
   python server.py
   ```
   To run the server and set it up
4. **Optional: Use ngrok to host**
   Set up ngrok to host and forward the server to an endpoint available outside the host network onto the internet
   ```bash
   ngrok http 0.0.0.0:5000
   ```

---

That's pretty much it, thanks!
