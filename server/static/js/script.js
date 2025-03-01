document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const videoUrl = document.getElementById('video_url').value;
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');

    // Show loading spinner
    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ 'video_url': videoUrl })
        });
        const data = await response.json();

        if (response.ok) {
            displayResults(data);
        } else {
            alert(data.error || 'Something went wrong!');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        loading.classList.add('hidden');
    }
});

function displayResults(data) {
    const summaryDiv = document.getElementById('summary');
    const keyPhrasesDiv = document.getElementById('keyPhrases');
    const suggestionsDiv = document.getElementById('suggestions');
    const commentsTableDiv = document.getElementById('commentsTable');
    const results = document.getElementById('results');

    // Summary with Chart
    summaryDiv.innerHTML = `
        <h3 class="text-lg font-semibold">Sentiment Summary</h3>
        <p>Positive: ${data.summary.positive} | Negative: ${data.summary.negative} | Neutral: ${data.summary.neutral} | Total: ${data.summary.total}</p>
        <canvas id="sentimentChart" class="mt-4"></canvas>
    `;
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [data.summary.positive, data.summary.negative, data.summary.neutral],
                backgroundColor: ['#34D399', '#F87171', '#9CA3AF']
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'top' } }
        }
    });

    // Key Phrases
    keyPhrasesDiv.innerHTML = `
        <h3 class="text-lg font-semibold">Top Negative Key Phrases</h3>
        <p>${data.key_phrases.length ? data.key_phrases.join(', ') : 'None detected'}</p>
    `;

    // Suggestions
    suggestionsDiv.innerHTML = `
        <h3 class="text-lg font-semibold">Suggestions</h3>
        <p>${data.suggestions.join(' ')}</p>
    `;

    // Comments Table
    commentsTableDiv.innerHTML = `
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-gray-200">
                    <th class="p-2">Author</th>
                    <th class="p-2">Comment</th>
                    <th class="p-2">Sentiment</th>
                    <th class="p-2">Likes</th>
                </tr>
            </thead>
            <tbody>
                ${data.comments.map(comment => `
                    <tr class="border-b">
                        <td class="p-2">${comment.author}</td>
                        <td class="p-2">${comment.text}</td>
                        <td class="p-2 ${comment.sentiment_label === 'positive' ? 'text-green-600' : comment.sentiment_label === 'negative' ? 'text-red-600' : 'text-gray-600'}">${comment.sentiment_label}</td>
                        <td class="p-2">${comment.like_count}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    results.classList.remove('hidden');
}