// Enhanced dayaChart.js with Month and Week Filter Dropdowns
document.addEventListener('DOMContentLoaded', () => {
    // Getting data from the HTML data attributes
    const chartElement = document.getElementById('dayaChart');
    
    // Parse the data from data attributes
    const rawLabels = JSON.parse(chartElement.dataset.labels || '[]');
    const rawData = JSON.parse(chartElement.dataset.data || '[]');
    
    // Store the original data for filtering
    const originalData = {
        labels: [...rawLabels],
        data: [...rawData]
    };
    
    // Format dates for better display and store data by month and week
    const months = {};
    const formattedLabels = [];
    
    rawLabels.forEach((dateStr, index) => {
        const date = new Date(dateStr);
        
        // Format the label
        const formatted = {
            full: dateStr,
            day: new Intl.DateTimeFormat('id', { weekday: 'short' }).format(date),
            date: date.getDate(),
            time: new Intl.DateTimeFormat('id', { hour: '2-digit', minute: '2-digit' }).format(date),
            // Store year and month information for filtering
            year: date.getFullYear(),
            month: date.getMonth(),
            // Calculate the week number within the month (1-5)
            weekInMonth: Math.ceil(date.getDate() / 7)
        };
        
        formattedLabels.push(formatted);
        
        // Create month and week structure for filters
        const monthKey = `${formatted.year}-${formatted.month}`;
        if (!months[monthKey]) {
            const monthName = new Intl.DateTimeFormat('id', { month: 'long', year: 'numeric' }).format(date);
            months[monthKey] = {
                name: monthName,
                weeks: {},
                allData: { labels: [], data: [] }
            };
        }
        
        const weekKey = formatted.weekInMonth;
        if (!months[monthKey].weeks[weekKey]) {
            months[monthKey].weeks[weekKey] = {
                labels: [],
                data: []
            };
        }
        
        // Add data to appropriate month and week
        months[monthKey].weeks[weekKey].labels.push(dateStr);
        months[monthKey].weeks[weekKey].data.push(rawData[index]);
        
        // Also add to the "all data for this month" collection
        months[monthKey].allData.labels.push(dateStr);
        months[monthKey].allData.data.push(rawData[index]);
    });
    
    const ctx = chartElement.getContext('2d');
    
    // Create the chart
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedLabels.map(l => `${l.day}, ${l.date} - ${l.time}`),
            datasets: [{
                label: 'Daya (kWh)',
                data: rawData,
                borderColor: 'rgb(34, 197, 94)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2,
                pointRadius: function(context) {
                    // Show points only on larger screens or when hovered
                    return window.innerWidth < 640 ? 2 : 4;
                },
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(34, 197, 94)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onResize: function(chart, size) {
                // Update point size when resizing
                chart.data.datasets[0].pointRadius = size.width < 640 ? 2 : 4;
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: function() {
                                return window.innerWidth < 640 ? 10 : 12;
                            }
                        },
                        callback: function(value) {
                            // Format the y-axis labels
                            return value + ' W';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Daya (kWh)',
                        font: {
                            size: function() {
                                return window.innerWidth < 640 ? 12 : 14;
                            },
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: function() {
                            return window.innerWidth < 640 ? 45 : 30;
                        },
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: function() {
                            // Show fewer ticks on small screens
                            return window.innerWidth < 640 ? 4 : 7;
                        },
                        font: {
                            size: function() {
                                return window.innerWidth < 640 ? 8 : 10;
                            }
                        },
                        callback: function(val, index) {
                            // Simplify labels on small screens
                            const item = formattedLabels[index];
                            if (!item) return '';
                            
                            if (window.innerWidth < 640) {
                                return `${item.day} ${item.time}`;
                            }
                            return `${item.day}, ${item.date} - ${item.time}`;
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: function() {
                        return window.innerWidth < 640 ? 'bottom' : 'top';
                    },
                    labels: {
                        boxWidth: function() {
                            return window.innerWidth < 640 ? 12 : 40;
                        },
                        font: {
                            size: function() {
                                return window.innerWidth < 640 ? 10 : 12;
                            }
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    padding: 10,
                    cornerRadius: 4,
                    titleFont: {
                        size: function() {
                            return window.innerWidth < 640 ? 12 : 14;
                        }
                    },
                    bodyFont: {
                        size: function() {
                            return window.innerWidth < 640 ? 11 : 13;
                        }
                    },
                    callbacks: {
                        title: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const fullDate = formattedLabels[index]?.full;
                            if (!fullDate) return '';
                            
                            const date = new Date(fullDate);
                            
                            return new Intl.DateTimeFormat('id', { 
                                weekday: 'long', 
                                year: 'numeric', 
                                month: 'long', 
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            }).format(date);
                        },
                        label: function(context) {
                            return `Penggunaan: ${context.parsed.y} kWh`;
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    // Function to update chart data
    function updateChart(labels, data) {
        // Clear existing formatted labels
        formattedLabels.length = 0;
        
        // Update the formatted labels
        labels.forEach(dateStr => {
            const date = new Date(dateStr);
            formattedLabels.push({
                full: dateStr,
                day: new Intl.DateTimeFormat('id', { weekday: 'short' }).format(date),
                date: date.getDate(),
                time: new Intl.DateTimeFormat('id', { hour: '2-digit', minute: '2-digit' }).format(date)
            });
        });
        
        // Update chart data
        chart.data.labels = formattedLabels.map(l => `${l.day}, ${l.date} - ${l.time}`);
        chart.data.datasets[0].data = data;
        
        // Update the chart
        chart.update();
    }
    
    // Function to apply filter based on month and week
    function applyFilter(monthKey, weekKey = null) {
        if (!monthKey) {
            // Show all data if no month selected
            updateChart(originalData.labels, originalData.data);
            return;
        }
        
        const monthData = months[monthKey];
        if (!monthData) {
            console.error('Month data not found:', monthKey);
            return;
        }
        
        if (weekKey === null || weekKey === 'all') {
            // Show all data for the selected month
            updateChart(monthData.allData.labels, monthData.allData.data);
        } else {
            // Show data for the specific week in the selected month
            const weekData = monthData.weeks[weekKey];
            if (weekData) {
                updateChart(weekData.labels, weekData.data);
            } else {
                console.error('Week data not found:', weekKey);
            }
        }
    }
    
    // Create filter controls
    function createFilterControls() {
        // Create filter container
        const filterContainer = document.createElement('div');
        filterContainer.className = 'mb-6';
        
        // Create filters row for side-by-side arrangement
        const filtersRow = document.createElement('div');
        filtersRow.className = 'grid grid-cols-1 md:grid-cols-2 gap-4';
        filterContainer.appendChild(filtersRow);
        
        // Create month filter column
        const monthFilterCol = document.createElement('div');
        monthFilterCol.className = 'flex items-center';
        
        const monthLabel = document.createElement('span');
        monthLabel.className = 'text-sm font-medium mr-2';
        monthLabel.textContent = 'Bulan:';
        monthFilterCol.appendChild(monthLabel);
        
        // Create month select
        const monthSelect = document.createElement('select');
        monthSelect.className = 'flex-grow px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-1 focus:ring-green-500 focus:border-green-500';
        
        // Add option for all data
        const allOption = document.createElement('option');
        allOption.value = '';
        allOption.textContent = 'Semua Data';
        monthSelect.appendChild(allOption);
        
        // Sort months by date (newest first)
        const sortedMonthKeys = Object.keys(months).sort().reverse();
        
        // Add month options
        sortedMonthKeys.forEach(monthKey => {
            const option = document.createElement('option');
            option.value = monthKey;
            option.textContent = months[monthKey].name;
            monthSelect.appendChild(option);
        });
        
        monthFilterCol.appendChild(monthSelect);
        filtersRow.appendChild(monthFilterCol);
        
        // Create week filter column
        const weekFilterCol = document.createElement('div');
        weekFilterCol.className = 'flex items-center';
        
        const weekLabel = document.createElement('span');
        weekLabel.className = 'text-sm font-medium mr-2';
        weekLabel.textContent = 'Minggu:';
        weekFilterCol.appendChild(weekLabel);
        
        // Create week select dropdown
        const weekSelect = document.createElement('select');
        weekSelect.className = 'flex-grow px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-1 focus:ring-green-500 focus:border-green-500';
        weekFilterCol.appendChild(weekSelect);
        
        filtersRow.appendChild(weekFilterCol);
        
        // Initially disable week filter
        weekSelect.disabled = true;
        
        // Function to update week options based on selected month
        function updateWeekOptions(monthKey) {
            // Clear previous options
            weekSelect.innerHTML = '';
            
            if (!monthKey) {
                weekSelect.disabled = true;
                return;
            }
            
            const monthData = months[monthKey];
            if (!monthData) {
                weekSelect.disabled = true;
                return;
            }
            
            // Enable the week select
            weekSelect.disabled = false;
            
            // Create "All Weeks" option
            const allWeeksOption = document.createElement('option');
            allWeeksOption.value = 'all';
            allWeeksOption.textContent = 'Semua Minggu';
            weekSelect.appendChild(allWeeksOption);
            
            // Create options for each week
            const weekKeys = Object.keys(monthData.weeks).sort((a, b) => parseInt(a) - parseInt(b));
            
            weekKeys.forEach(weekKey => {
                const option = document.createElement('option');
                option.value = weekKey;
                option.textContent = `Minggu ${weekKey}`;
                weekSelect.appendChild(option);
            });
            
            // Set default to "All Weeks"
            weekSelect.value = 'all';
        }
        
        // Handle month select change
        monthSelect.addEventListener('change', () => {
            const monthKey = monthSelect.value;
            
            if (!monthKey) {
                // Show all data
                applyFilter(null);
                updateWeekOptions(null);
            } else {
                // Update week options and show all data for the selected month
                updateWeekOptions(monthKey);
                applyFilter(monthKey, 'all');
            }
        });
        
        // Handle week select change
        weekSelect.addEventListener('change', () => {
            const monthKey = monthSelect.value;
            const weekKey = weekSelect.value;
            
            applyFilter(monthKey, weekKey);
        });
        
        // Insert filter controls before the chart
        const chartParent = chartElement.parentElement;
        chartParent.parentElement.insertBefore(filterContainer, chartParent);
        
        // Initialize with the most recent month if available
        if (sortedMonthKeys.length > 0) {
            const latestMonthKey = sortedMonthKeys[0];
            monthSelect.value = latestMonthKey;
            updateWeekOptions(latestMonthKey);
            applyFilter(latestMonthKey, 'all');
        }
    }
    
    // Create and initialize the filter controls
    createFilterControls();
    
    // Update chart on window resize for responsive behavior
    window.addEventListener('resize', () => {
        chart.update();
    });
});