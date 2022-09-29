last_timestamp = 0.0

function cat_new_tr_item(item){
    if(item["time"] > last_timestamp){
        last_timestamp = item["time"];
    } else{
        return;
    }
    var action_list_table = $("#action-list-table");
    var total_item = $("#action-list-table").find("tr").length;
    seq_size = 16;
    window_size = 8;
    max_item_num = 13;
    if(item["role"] == "sender"){
        Sw = item["data"]["Sw"];
        Sf = item["data"]["Sf"];
        Sn = item["data"]["Sn"];
        // sender: makeframe
        if(item["action"] == "makeframe"){
            var ItemHTML = $(`<tr class="active">`
            +`<td class="text-center">${  
            (function (){
                text = `<h5>`;
                text += `<span class="label label-default">D</span>`;
                text += `<span class="label label-primary">Seq ${item["data"]["seq"]}</span>`
                text += `<span class="label label-info">${item["data"]["payload"]}</span>`
                text += `<span class="label label-default">CRC32</span>`
                text += `</h5>`;
                return text;
            })()}</td>`
            +`<td class="text-center"> 
            <h5><span class="label label-success">
            Make Frame(${item["data"]["seq"]})
            </span>
            </h5>
            </td>`
            +`<td class="text-center"> --- </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // sender: send
        if(item["action"] == "send"){
            var ItemHTML = $(`<tr class="active">`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Sf >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Sf-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`;
                    text += ((Sf-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Sf; i < Sn; i++) { 
                    text += `<span class="label label-warning">`;
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let j = Sn; j < Sf+Sw; j++) { 
                    text += `<span class="label label-primary">`
                    text += (j%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Sf+Sw)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Sf+Sw+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`<td class="text-center"> 
            <h5><span class="label label-info">
            Frame(${item["data"]["seq"]}) 
            </span>
            <img src="/static/img/right_arrow.png" style="margin-left: 10px;width: 25px;"/>
            </h5>
            </td>`
            +`<td class="text-center"> --- </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // sender: resend
        if(item["action"] == "resend"){
            var ItemHTML = $(`<tr class="warning">`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Sf >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Sf-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`;
                    text += ((Sf-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Sf; i < Sn; i++) { 
                    text += `<span class="label label-warning">`;
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let j = Sn; j < Sf+Sw; j++) { 
                    text += `<span class="label label-primary">`
                    text += (j%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Sf+Sw)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Sf+Sw+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`<td class="text-center"> 
            <h5><span class="label label-info">
            Frame(${item["data"]["seq"]}) 
            </span>
            <span class="label label-warning" style="margin-left: 10px;">
            Resend: ${item["data"]["reason"]}
            </span>
            <img src="/static/img/right_arrow.png" style="margin-left: 10px;width: 25px;"/>
            </h5>
            </td>`
            +`<td class="text-center"> --- </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // sender: loss
        if(item["action"] == "loss"){
            var ItemHTML = $(`<tr class="danger">`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Sf >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Sf-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`;
                    text += ((Sf-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Sf; i < Sn; i++) { 
                    text += `<span class="label label-warning">`;
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let j = Sn; j < Sf+Sw; j++) { 
                    text += `<span class="label label-primary">`
                    text += (j%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Sf+Sw)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Sf+Sw+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`<td class="text-center"> 
            <h5><span class="label label-info">
            Frame(${item["data"]["seq"]}) 
            </span>
            <img src="/static/img/right_arrow.png" style="margin-left: 10px;width: 25px;"/>
            <span class="label label-danger">
            Loss!
            </span>
            </h5>
            </td>`
            +`<td class="text-center"> --- </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // sender: badframe
        if(item["action"] == "badframe"){
            var ItemHTML = $(`<tr class="warning">`
            +`<td class="text-center">
            ${  
            (function (){
                text = `<h5>`
                text += `<span class="label label-danger">Raw: ${item["data"]["raw_data"]}</span>`
                text += `</h5>`;
                return text;
            })()
            }
            </td>`            
            +`<td class="text-center"> 
            <h5><span class="label label-danger">
            Error: ${item["data"]["reason"]}
            </span>
            </h5>
            </td>`
            +`<td class="text-center"> --- </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
    }
    // ==================================================================================================
    if(item["role"] == "receiver"){
        seq = item["data"]["seq"] % seq_size;
        Rn = item["data"]["Rn"];
        slots = item["data"]["slots"];
        console.log(slots);
        // receiver: deliver
        if(item["action"] == "deliver"){
            var ItemHTML = $(`<tr class="active">`
            +`<td class="text-center"> --- </td>`
            +`<td class="text-center"> 
            <h5><span class="label label-success">
            Deliver Data(${item["data"]["seq"]})
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = `<h5>`
                text += `<span class="label label-info">Data: ${item["data"]["payload"]}</span>`
                text += `</h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // receiver: badframe
        if(item["action"] == "badframe"){
            var ItemHTML = $(`<tr class="warning">`
            +`<td class="text-center"> --- </td>`
            +`<td class="text-center"> 
            <h5><span class="label label-danger">
            Error: ${item["data"]["reason"]}
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = `<h5>`
                text += `<span class="label label-danger">Raw: ${item["data"]["raw_data"]}</span>`
                text += `</h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // receiver: ack
        if(item["action"] == "ack"){
            var ItemHTML = $(`<tr class="active">`
            +`<td class="text-center">---</td>`
            +`<td class="text-center"> 
            <h5>
            <img src="/static/img/left_arrow.png" style="margin-right: 10px;width: 25px;"/>
            <span class="label label-success">
            ACK(${seq})
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Rn >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Rn-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`
                    text += ((Rn-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Rn; i < Rn+window_size; i++) { 
                    if(slots[i%seq_size] == true){
                        lable_type = "success";
                    } else{
                        lable_type = "primary";
                    }
                    text += `<span class="label label-${lable_type}">`
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Rn+window_size)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Rn+window_size+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // receiver: nak
        if(item["action"] == "nak"){
            var ItemHTML = $(`<tr class="active">`
            +`<td class="text-center">---</td>`
            +`<td class="text-center"> 
            <h5>
            <img src="/static/img/left_arrow.png" style="margin-right: 10px;width: 25px;"/>
            <span class="label label-warning">
            NAK(${seq})
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Rn >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Rn-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`
                    text += ((Rn-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }                
                for (let i = Rn; i < Rn+window_size; i++) { 
                    if(slots[i%seq_size] == true){
                        lable_type = "success";
                    } else{
                        lable_type = "primary";
                    }
                    text += `<span class="label label-${lable_type}">`
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Rn+window_size)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Rn+window_size+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // receiver: ackloss
        if(item["action"] == "ackloss"){
            var ItemHTML = $(`<tr class="danger">`
            +`<td class="text-center">---</td>`
            +`<td class="text-center"> 
            <h5>
            <img src="/static/img/left_arrow.png" style="margin-right: 10px;width: 25px;"/>
            <span class="label label-danger" style="margin-right: 10px;">
            Loss!
            </span>
            <span class="label label-warning">
            ACK(${seq})
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Rn >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Rn-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`
                    text += ((Rn-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Rn; i < Rn+window_size; i++) { 
                    if(slots[i%seq_size] == true){
                        lable_type = "success";
                    } else{
                        lable_type = "primary";
                    }
                    text += `<span class="label label-${lable_type}">`
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Rn+window_size)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Rn+window_size+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
        // receiver: nakloss
        if(item["action"] == "nakloss"){
            var ItemHTML = $(`<tr class="danger">`
            +`<td class="text-center">---</td>`
            +`<td class="text-center"> 
            <h5>
            <img src="/static/img/left_arrow.png" style="margin-right: 10px;width: 25px;"/>
            <span class="label label-danger" style="margin-right: 10px;">
            Loss!
            </span>
            <span class="label label-warning">
            NAK(${seq})
            </span>
            </h5>
            </td>`
            +`<td class="text-center">
            ${  
            (function (){
                text = "<h5>"
                if(Rn >= 2){
                    text += `<span class="label label-default">`;
                    text += ((Rn-2)%seq_size)+"&nbsp;";
                    text += `</span>`;
                    text += `<span class="label label-default">`
                    text += ((Rn-1)%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                for (let i = Rn; i < Rn+window_size; i++) { 
                    if(slots[i%seq_size] == true){
                        lable_type = "success";
                    } else{
                        lable_type = "primary";
                    }
                    text += `<span class="label label-${lable_type}">`
                    text += (i%seq_size)+"&nbsp;";
                    text += `</span>`;
                }
                text += `<span class="label label-default">`;
                text += ((Rn+window_size)%seq_size)+"&nbsp;";
                text += `</span>`;
                text += `<span class="label label-default">`;
                text += ((Rn+window_size+1)%seq_size)+"&nbsp;";
                text += `</span></h5>`;
                return text;
            })()
            }
            </td>`
            +`</tr>`);
            if(total_item > max_item_num){
                $("#action-list-table tr:first").remove();
            }
            ItemHTML.appendTo(action_list_table);
        }
    }
}

function get_new_action() {
    $.ajax({
        type: "GET",
        url: "/action/get",
        dataType: "json",
        success: function (data) {
            console.log(data);
            data.forEach(cat_new_tr_item);
        }
    });
}

function set_loss_signal(){
    $.ajax({
        type: "GET",
        url: "/cmd/set?field=loss&value=true",
        dataType: "json"
    });
}    

function set_timeout_signal(){
    $.ajax({
        type: "GET",
        url: "/cmd/set?field=timeout&value=true",
        dataType: "json"
    });
}    

function set_damage_signal(){
    $.ajax({
        type: "GET",
        url: "/cmd/set?field=damage&value=true",
        dataType: "json"
    });
}    

function pageRefresh() {
    get_new_action();
}

setInterval(pageRefresh, 400);  //0.4秒刷新一次
