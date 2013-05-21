loadSource = function(fileUrl, codeNode){
    $.get(fileUrl, function(respons) {
        //codeNode.text("loading...").html();
        //alert("ghjk");
        codeNode.text(respons).html();
        hljs.highlightBlock(codeNode[0]);
    })
        .fail(function() {codeNode.text("This file doesn't exist.")});
}