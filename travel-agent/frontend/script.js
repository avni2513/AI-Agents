async function planTrip() {
    const destination =
        document.getElementById("destination").value;

    const days =
        document.getElementById("days").value;

    const budget =
        document.getElementById("budget").value;

    const interests =
        document.getElementById("interests").value;

    const result =
        document.getElementById("result");

    if (!destination || !days) {
        result.innerHTML =
            "<p>Please enter destination and number of days.</p>";
        return;
    }

    result.innerHTML =
        "<p>✨ Planning your trip...</p>";

    try {
        const response = await fetch(
            "http://127.0.0.1:8000/plan",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    destination: destination,
                    days: Number(days),
                    budget: budget,
                    interests: interests
                })
            }
        );

        const data = await response.json();

        result.innerHTML = `
            <h2>Your Travel Plan</h2>
            <pre>${data.result}</pre>
        `;

    } catch (error) {
        result.innerHTML =
            "<p>❌ Could not connect to the Travel Agent backend.</p>";
    }
}