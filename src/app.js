const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.get('/api/health', (req, res) => {
    res.json({
        status: 'OK',
        timestamp: new Date().toISOString(),
        message: 'Racing Simple API is running'
    });
});

// Sample racing data endpoint
app.get('/api/races', (req, res) => {
    const sampleRaces = [
        {
            id: 1,
            name: "Sample Race 1",
            time: "2:00 PM",
            track: "Sample Track",
            distance: "1 mile",
            horses: [
                { name: "Thunder Bolt", odds: "3/1", jockey: "J. Smith" },
                { name: "Lightning Fast", odds: "5/2", jockey: "M. Johnson" },
                { name: "Speed Demon", odds: "4/1", jockey: "A. Williams" }
            ]
        },
        {
            id: 2,
            name: "Sample Race 2", 
            time: "3:30 PM",
            track: "Sample Track",
            distance: "1.5 miles",
            horses: [
                { name: "Storm Chaser", odds: "2/1", jockey: "R. Davis" },
                { name: "Wind Runner", odds: "7/2", jockey: "S. Brown" },
                { name: "Fire Starter", odds: "6/1", jockey: "T. Wilson" }
            ]
        }
    ];
    
    res.json({
        success: true,
        data: sampleRaces,
        count: sampleRaces.length
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        success: false,
        message: 'Something went wrong!',
        error: process.env.NODE_ENV === 'development' ? err.message : {}
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        success: false,
        message: 'Route not found'
    });
});

app.listen(PORT, () => {
    console.log(`Racing Simple server is running on port ${PORT}`);
    console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`Visit: http://localhost:${PORT}`);
});