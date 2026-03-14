const db = new Dexie("ChatLinkDB");

db.version(1).stores({
    chat_history:"friend"
});

document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    socket.on('new_message', (data) => {
        receivedMsgDisplay(data.chat_name, data.message, data.sender);
    });

    socket.on('uploaded_files', (data) => {
        console.log("received a file")
        console.log(data.url)
        receivedMsgDisplayFile(data.chat_name, data.url, data.name);
    });
});

//receiving files
async function receivedMsgDisplayFile(chat_name, fileURL, filename){
    let messageDisplayer = document.querySelector(".messages-container");
    const date_time = new Date().toISOString();
    
    let msgCont = document.createElement("div");
    msgCont.className = "recieve-message";
    msgCont.innerHTML = `
    <div class="chat-box">
        <a href="${fileURL}" download>
            <img src="/static/images/file.png">
            ${filename}
        </a>
    </div>
    `;
    console.log("came here")

    const newMsg = await buildMsg("them", filename, date_time);
    await saveMessage(chat_name, newMsg);

    messageDisplayer.appendChild(msgCont);
    //console.log(message);
}

async function fileURL(file){
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/upload_file", {
        method: "POST",
        body: formData
    });

    const data = await response.json();
    return data;
}

async function messageDisplay(){
    let messageDisplayer = document.querySelector(".messages-container");
    
    const files = document.querySelector("#file-upload").files
    let sent_file = null;

    let msgCont = document.createElement("div");
    msgCont.className = "send-message";

    if(files.length > 0){
        const file = files[0];
        const data = await fileURL(file);
        sent_file = {
            filename: file.name,
            type:file.type,
            size: file.size,
            url: data.url
        }
        msgCont.innerHTML = fileMsgBuild(file);
        messageDisplayer.appendChild(msgCont);
    }

    let name = messageDisplayer.dataset.friend;
    
    let input = document.querySelector("#message-input");
    const message = input.value;
    const person = isPerson(name);

    if(person === false)
        name = name.split("-")[0];
    

    if(message.trim() === ""){
        await fetch("/send_gmessage", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                msgType: `${msg_type}`,
                name: `${name}`,
                message: `${message}`,
                file: sent_file
            })
        });
        return;
    }

    const date_time = new Date().toISOString();

    msgCont.innerHTML = `
                <div class="chat-box">
                    <p>
                    ${message}
                    </p>
                </div>
    `;
    
    newMsg = await buildMsg("me", message, date_time);
    await saveMessage(name, newMsg);


    messageDisplayer.appendChild(msgCont);
    console.log(message);

    input.value = "";

    console.log(sent_file)
    await fetch("/send_message", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            person: `${person}`,
            name: `${name}`,
            message: `${message}`,
            file: sent_file
        })
    });

}

function isPerson(FriendName){
    let fn = FriendName.split("-");
    if (fn.length > 1) return false;
    
    return true;
}

//for receiving msg
async function receivedMsgDisplay(chat_name, message, sender=null){
    let messageDisplayer = document.querySelector(".messages-container");
    const date_time = new Date().toISOString();
    
    let msgCont = document.createElement("div");
    msgCont.className = "recieve-message";
    msgCont.innerHTML = `
                 ${sender ? `<h5>${sender}</h5>` : ""}
                    <p>
                    ${message}
                    </p>
    `;
    console.log("came here")

    const newMsg = await buildMsg("them", message, date_time);
    await saveMessage(chat_name, newMsg);

    messageDisplayer.appendChild(msgCont);
    console.log(message);
}

function buildMsg(sender, message, date_time){
    return { sender, message, date_time };
}

async function saveMessage(friendName, newMsg){
    const record = await db.chat_history.get(friendName) || {friend:friendName, messages: []};

    record.messages.push(newMsg);
    await db.chat_history.put(record);
}

async function loadChat(friendName){
    const record = await db.chat_history.get(friendName);
    return record?.messages || [];
}

// async function openChat(chat_name) {
//     const messageDisplayer = document.querySelector(".messages-container");
//     messageDisplayer.dataset.friend = friendName;
//     const messages = await loadChat(chat_name);
//     messageDisplayer.innerHTML = ""; // clear current display

//     messages.forEach(msg => {
//         let msgCont = document.createElement("div");
//         msgCont.className = msg.sender === "me" ? "sent-message" : "received-message";
//         msgCont.innerHTML = `
//             <div class="chat-box">
//                 ${msg.sender === "them" ? `<h5>${chat_name}</h5>` : ""}
//                 <p>${msg.message}</p>
//                 <small>${msg.date_time}</small>
//             </div>
//         `;
//         messageDisplayer.appendChild(msgCont);
//     });
// }


// const urlParams = new URLSearchParams(window.location.search);
// const chat_name = urlParams.get('friend'); 