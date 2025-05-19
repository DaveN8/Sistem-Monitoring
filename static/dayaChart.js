document.addEventListener('DOMContentLoaded', () => {
    const chartElement = document.getElementById('dayaChart');
    if (!chartElement) return;

    const rawLabels = JSON.parse(chartElement.dataset.labels || '[]');
    const rawData = JSON.parse(chartElement.dataset.data || '[]');

    const days = {};
    const months = {};

    rawLabels.forEach((dateStr, i) => {
        const date = new Date(dateStr);
        const y = date.getFullYear();
        const m = date.getMonth() + 1;
        const d = date.getDate();
        const weekInMonth = Math.ceil(d / 7);

        const dayKey = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        const monthKey = `${y}-${String(m).padStart(2, '0')}`;
        const weekKey = `W${weekInMonth}`;

        if (!months[monthKey]) {
            months[monthKey] = {
                name: new Intl.DateTimeFormat('id', { month: 'long', year: 'numeric' }).format(date),
                weeks: {},
                daily: {}
            };
        }

        if (!months[monthKey].weeks[weekKey]) {
            months[monthKey].weeks[weekKey] = { total: 0 };
        }

        if (!months[monthKey].daily[dayKey]) {
            months[monthKey].daily[dayKey] = 0;
        }

        months[monthKey].weeks[weekKey].total += rawData[i];
        months[monthKey].daily[dayKey] += rawData[i];
        days[dayKey] = months[monthKey].daily[dayKey];
    });

    const ctx = chartElement.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Penggunaan kWh',
                data: [],
                backgroundColor: 'rgba(34, 197, 94, 0.4)',
                borderColor: 'rgb(34, 197, 94)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'kWh'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        autoSkip: false
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `Penggunaan: ${context.parsed.y.toFixed(3)} kWh`;
                        }
                    }
                }
            }
        }
    });

    // Filter UI
    const controls = document.createElement('div');
    controls.className = 'flex flex-wrap justify-end gap-4 mb-4';

    const monthSelect = document.createElement('select');
    monthSelect.className = 'px-3 py-1 rounded border';
    monthSelect.innerHTML = `<option value="">Semua</option>`;
    Object.entries(months).forEach(([key, val]) => {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = val.name;
        monthSelect.appendChild(opt);
    });

    const weekSelect = document.createElement('select');
    weekSelect.className = 'px-3 py-1 rounded border';
    weekSelect.disabled = true;
    controls.appendChild(monthSelect);
    controls.appendChild(weekSelect);

    chartElement.closest('.mt-6').prepend(controls);

    monthSelect.addEventListener('change', () => {
        const monthKey = monthSelect.value;
        weekSelect.innerHTML = '';
        weekSelect.disabled = !monthKey;

        if (monthKey) {
            const weekKeys = Object.keys(months[monthKey].weeks).sort();
            weekSelect.innerHTML = `<option value="all">Semua Minggu</option>`;
            weekKeys.forEach(week => {
                const opt = document.createElement('option');
                opt.value = week;
                opt.textContent = `Minggu ${week.replace('W', '')}`;
                weekSelect.appendChild(opt);
            });
            updateChartWithWeek(monthKey, 'all');
        } else {
            const lastWeekMonth = Object.keys(months).slice(-1)[0];
            const lastWeekData = Object.entries(months[lastWeekMonth].daily).slice(-7);
            const labels = lastWeekData.map(([k]) => k);
            const data = lastWeekData.map(([, v]) => v);
            updateChart(labels, data);
        }
    });

    weekSelect.addEventListener('change', () => {
        updateChartWithWeek(monthSelect.value, weekSelect.value);
    });

    function updateChart(labels, data) {
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        chart.update();
    }

    function updateChartWithWeek(monthKey, weekKey) {
        const month = months[monthKey];
        if (!month) return;

        if (weekKey === 'all') {
            const labels = [];
            const data = [];

            Object.entries(month.weeks).forEach(([key, val]) => {
                labels.push(`Minggu ${key.replace('W', '')}`);
                data.push(Number(val.total.toFixed(3)));
            });
            updateChart(labels, data);
        } else {
            const dayData = Object.entries(month.daily).filter(([dateStr]) => {
                const d = new Date(dateStr);
                return Math.ceil(d.getDate() / 7) == weekKey.replace('W', '');
            });
            const labels = dayData.map(([d]) => d);
            const data = dayData.map(([, v]) => Number(v.toFixed(3)));
            updateChart(labels, data);
        }
    }

    // Init: tampilkan minggu terakhir
    const recentMonthKey = Object.keys(months).slice(-1)[0];
    const recentDays = Object.entries(months[recentMonthKey].daily).slice(-7);
    updateChart(recentDays.map(([k]) => k), recentDays.map(([, v]) => v));
});
