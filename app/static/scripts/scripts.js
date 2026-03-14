const db = new Dexie("ChatLinkDB");

db.version(1).stores({
    chat_history:"friend"
});

document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    socket.on('new_message', (data) => {
        receivedMsgDisplay(data.chat_name, data.message);
    });

    socket.on('uploaded_files', (data) => {

        receivedMsgDisplayFile(data.chat_name, data.url);
    });
});

//receiving files
async function receivedMsgDisplayFile(chat_name, filename){
    let messageDisplayer = document.querySelector(".messages-container");
    const date_time = new Date().toISOString();
    
    let msgCont = document.createElement("div");
    msgCont.className = "recieve-message";
    msgCont.innerHTML = `
    <div class="chat-box">
        <a href="${data.url}" download>
            <img src="/static/images/file.png">
            ${file.name}
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
    let input = document.querySelector("#message-input");
    let messageDisplayer = document.querySelector(".messages-container");
    const chat_name = messageDisplayer.dataset.friend;
    const files = document.querySelector("#file-upload").files
    let sent_file = null;

    const formData = new FormData();

    let msgCont = document.createElement("div");
    msgCont.className = "send-message";

    if(files.length > 0){
        file = files[0];
        //console.log(file);
        const data = await fileURL(file, formData);
        //console.log(data.url); // URL of uploaded file
        //console.log(data);

        sent_file = {
            filename: file.name,
            type:file.type,
            size: file.size,
            url: data.url
        }

        msgCont.innerHTML = fileMsgBuild(file);
        messageDisplayer.appendChild(msgCont);
    }

    const message = input.value;

    if(message.trim() === ""){
        await fetch("/send_message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                friend: `${chat_name}`,
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
    await saveMessage(chat_name, newMsg);


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
            friend: `${chat_name}`,
            message: `${message}`,
            file: sent_file
        })
    });

}

function fileMsgBuild(file){
        return `
            <div class="chat-box">
                <p>
                    ${file.name}
                    <img src="/static/images/file.png">
                </p>
            </div>
        `;
}


// async function messageDisplay(){
//     let input = document.querySelector("#message-input");
//     let messageDisplayer = document.querySelector(".messages-container");
//     const chat_name = messageDisplayer.dataset.friend;
//     const files = document.querySelector("#file-upload").files
//     let sent_file=null;

//     let msgCont = document.createElement("div");
//     msgCont.className = "send-message";

//     if (files.length > 0){
//         file = files[0]

//         const bytes = await file.arrayBuffer();

//         console.log(bytes)

//         sent_file = {
//             name: file.name,
//             size: file.size,
//             type: file.type,
//             data: bytes
//         };

//         msgCont.innerHTML = `
//             <div class="chat-box">
//                 <p>
//                     ${file.name}
//                     <img src="/static/images/file.png">
//                 </p>
//             </div>
//         `;

//         messageDisplayer.appendChild(msgCont);
//     }

//     console.log(chat_name)

//     console.log("Welcome to chatlink");
//     const message = input.value;

//     if(message.trim() === "") return;

//     const date_time = new Date().toISOString();

//     msgCont.innerHTML = `
//                 <div class="chat-box">
//                     <p>
//                     ${message}
//                     </p>
//                 </div>
//     `;
    
//     newMsg = await buildMsg("me", message, date_time);
//     await saveMessage(chat_name, newMsg);


//     messageDisplayer.appendChild(msgCont);
//     console.log(message);

//     input.value = "";

//     await fetch("/send_message", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json"
//         },
//         body: JSON.stringify({
//             friend: `${chat_name}`,
//             message: `${message}`,
//             file: sent_file
//         })
//     });
// }

//for receiving msg
async function receivedMsgDisplay(chat_name, message){
    let messageDisplayer = document.querySelector(".messages-container");
    const date_time = new Date().toISOString();
    
    let msgCont = document.createElement("div");
    msgCont.className = "recieve-message";
    msgCont.innerHTML = `
                <h5>${chat_name}</h5>
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

async function openChat(chat_name) {
    const messageDisplayer = document.querySelector(".messages-container");
    messageDisplayer.dataset.friend = friendName;
    const messages = await loadChat(chat_name);
    messageDisplayer.innerHTML = ""; // clear current display

    messages.forEach(msg => {
        let msgCont = document.createElement("div");
        msgCont.className = msg.sender === "me" ? "sent-message" : "received-message";
        msgCont.innerHTML = `
            <div class="chat-box">
                ${msg.sender === "them" ? `<h5>${chat_name}</h5>` : ""}
                <p>${msg.message}</p>
                <small>${msg.date_time}</small>
            </div>
        `;
        messageDisplayer.appendChild(msgCont);
    });
}


//save msg
async function saveMessage(friendName, newMsg){
    const record = await db.chat_history.get(friendName) || {friend:friendName, messages: []};

    record.messages.push(newMsg);
    await db.chat_history.put(record);
}

// load chat
async function loadChat(friendName){
    const record = await db.chat_history.get(friendName);
    return record?.messages || [];
}

function buildMsg(sender, message, date_time){
    return { sender, message, date_time };
}

const urlParams = new URLSearchParams(window.location.search);
const chat_name = urlParams.get('friend'); 

if (chat_name) { 
    document.querySelector('.messages-container').dataset.friend = chat_name;
    console.log(chat_name);
    openChat(chat_name);
}