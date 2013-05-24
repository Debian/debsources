function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

loadSource = function(fileUrl, codeNode){
    $.get(fileUrl, function(respons) {
        //respons = respons.replace("\r\n", "\n");
        respons = respons.split("\n");

        codeNode.text("");
        $.each(respons, function(n, elem) {
            codeNode.append(elem);
            codeNode.append("\n");
        })

        //codeNode.text(respons).html(); //displaying the code
        hljs.highlightBlock(codeNode[0]); //colorizing it
    })
        .fail(function() {codeNode.text("This file doesn't exist.")});
}