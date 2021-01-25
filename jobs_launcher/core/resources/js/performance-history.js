var performanceCharts = {}
var lastMetricName = null
var lastData = null
var colors = ['#82438CFF', '#327A5BFF', '#F4B400FF', '#2D538FFF', '#DB4437FF', '#4285F4FF', '#E8E541FF', '#24C959FF', '#00ACC1FF', '#FF7043FF']

function changeMetric(id, metric) {
    performanceCharts[id].chart.data.labels = performanceCharts[id].renderData[metric].labels
    performanceCharts[id].chart.data.datasets = performanceCharts[id].renderData[metric].datasets
    performanceCharts[id].chart.options = performanceCharts[id].optionsData[metric]
    performanceCharts[id].chart.update()
    lastMetricName = metric
    lastData = performanceCharts[id].renderData[metric]
    lastOptionsData = performanceCharts[id].optionsData[metric]
}

function showPartOfBuilds(id, number) {
    let totalElementNumber = lastData.labels.length
    let displayedElementsNumber = number
    if (number <= 0) {
        displayedElementsNumber = totalElementNumber
    } else {
        if (totalElementNumber < number) {
            displayedElementsNumber = totalElementNumber
        }
    }

    let dataset = {}
    dataset.label = lastData.datasets[0].label
    dataset.borderColor = lastData.datasets[0].borderColor
    performanceCharts[id].chart.data.labels = lastData.labels.slice(totalElementNumber - displayedElementsNumber, totalElementNumber)
    dataset.data = lastData.datasets[0].data.slice(totalElementNumber - displayedElementsNumber, totalElementNumber)
    performanceCharts[id].chart.data.datasets = [dataset]
    performanceCharts[id].chart.update()
}

function downloadCSV(id, metrics) {
    // generate file with csv data in browser
    let csvData = []
    csvData.push("build_number")
    csvData.push(`,${lastMetricName}%0A`)
    for (i in lastData.labels) {
        csvData.push(lastData.labels[i])
        csvData.push(`,${lastData.datasets[0].data[i]}%0A`)
    }
    csvData = csvData.join("").replaceAll("#", "%23")

    let content = `data:application/csv;charset=utf-8,${csvData}`
    let filename = `${id.replace("performanceChart-", "")}.csv`

    let fileLink = $("<a download='" + filename + "' href='" + content + "'></a>");
    // in Firefox it doesn't work without adding to body of document
    fileLink.appendTo("body");
    fileLink[0].click();
    fileLink.remove();
}