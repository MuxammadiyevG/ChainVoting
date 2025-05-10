// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Voting {
    address public admin;
    bool public electionStarted;
    bool public electionEnded;
    
    struct Candidate {
        uint id;
        string name;
        uint voteCount;
    }
    
    mapping(uint => Candidate) public candidates;
    mapping(address => bool) public voters;
    uint public candidatesCount;
    
    event VoteCast(address indexed voter, uint indexed candidateId);
    event CandidateAdded(uint indexed candidateId, string name);
    event ElectionStarted(uint timestamp);
    event ElectionEnded(uint timestamp);
    
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }
    
    modifier electionIsActive() {
        require(electionStarted, "Election has not started yet");
        require(!electionEnded, "Election has already ended");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        electionStarted = false;
        electionEnded = false;
    }
    
    function addCandidate(string memory _name) public onlyAdmin {
        require(!electionStarted, "Cannot add candidate after election has started");
        candidatesCount++;
        candidates[candidatesCount] = Candidate(candidatesCount, _name, 0);
        emit CandidateAdded(candidatesCount, _name);
    }
    
    function startElection() public onlyAdmin {
        require(!electionStarted, "Election has already started");
        require(candidatesCount > 0, "No candidates added");
        electionStarted = true;
        emit ElectionStarted(block.timestamp);
    }
    
    function endElection() public onlyAdmin {
        require(electionStarted, "Election has not started yet");
        require(!electionEnded, "Election has already ended");
        electionEnded = true;
        emit ElectionEnded(block.timestamp);
    }
    
    function vote(uint _candidateId) public electionIsActive {
        require(!voters[msg.sender], "You have already voted");
        require(_candidateId > 0 && _candidateId <= candidatesCount, "Invalid candidate ID");
        
        voters[msg.sender] = true;
        candidates[_candidateId].voteCount++;
        
        emit VoteCast(msg.sender, _candidateId);
    }
    
    function getCandidate(uint _candidateId) public view returns (uint, string memory, uint) {
        require(_candidateId > 0 && _candidateId <= candidatesCount, "Invalid candidate ID");
        Candidate memory c = candidates[_candidateId];
        return (c.id, c.name, c.voteCount);
    }
    
    function getCandidatesCount() public view returns (uint) {
        return candidatesCount;
    }
    
    function hasVoted(address _voter) public view returns (bool) {
        return voters[_voter];
    }
}