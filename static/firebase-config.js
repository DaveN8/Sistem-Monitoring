import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, 
         GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyC95VjtoAEvQAXxEEdbxuQSfw5oTIhaxfY",
  authDomain: "sistemdaya.firebaseapp.com",
  projectId: "sistemdaya",
  storageBucket: "sistemdaya.firebasestorage.app",
  messagingSenderId: "937187133208",
  appId: "1:937187133208:web:9bb0c6fa903d974cb5006d",
  measurementId: "G-3SFF40MG9Z"
};

  // Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

const db = getFirestore(app);

export { auth, provider, db };